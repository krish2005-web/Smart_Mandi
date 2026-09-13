from datetime import date,datetime
from flask import Blueprint,request,jsonify
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models import *
from ..utils.security import role_required,current_user
from ..utils.audit import audit
operator_bp=Blueprint('operator',__name__)

def assigned():
    return OperatorAssignment.query.filter_by(operator_id=get_jwt_identity()).first()
@operator_bp.get('/dashboard')
@role_required(Role.OPERATOR)
def dashboard():
    a=assigned()
    if not a:return jsonify(success=False,message='No centre assigned',error_code='NO_ASSIGNMENT'),403
    rows=Booking.query.join(ProcurementSlot).filter(ProcurementSlot.centre_id==a.centre_id,ProcurementSlot.slot_date==date.today()).all()
    return jsonify(success=True,data={'centre':a.centre_id,'today':[{'booking_id':b.booking_id,'status':b.status.value,'farmer':f'{b.farmer.first_name} {b.farmer.last_name}','slot':b.slot.start_time.strftime('%H:%M')} for b in rows]})
@operator_bp.post('/bookings/<uuid:booking_id>/check-in')
@role_required(Role.OPERATOR)
def checkin(booking_id):
    a=assigned();b=Booking.query.get_or_404(booking_id)
    if not a or b.slot.centre_id!=a.centre_id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    b.status=BookingStatus.IN_QUEUE;q=b.queue_entry;q.state='WAITING';q.checked_in_at=datetime.utcnow(); max_token=db.session.query(db.func.max(QueueEntry.token_number)).join(Booking).join(ProcurementSlot).filter(ProcurementSlot.centre_id==a.centre_id,ProcurementSlot.slot_date==date.today()).scalar() or 0;q.token_number=max_token+1;q.position=QueueEntry.query.join(Booking).join(ProcurementSlot).filter(ProcurementSlot.centre_id==a.centre_id,ProcurementSlot.slot_date==date.today(),QueueEntry.state=='WAITING').count();q.estimated_minutes=q.position*10;audit('CHECK_IN','BOOKING',b.id);db.session.commit();return jsonify(success=True,data={'token':q.token_number,'position':q.position})
@operator_bp.post('/bookings/<uuid:booking_id>/call-next')
@role_required(Role.OPERATOR)
def call_next(booking_id):
    a=assigned();b=Booking.query.get_or_404(booking_id)
    if not a or b.slot.centre_id!=a.centre_id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    b.status=BookingStatus.PROCESSING;b.queue_entry.state='PROCESSING';b.queue_entry.called_at=datetime.utcnow();db.session.commit();return jsonify(success=True)
