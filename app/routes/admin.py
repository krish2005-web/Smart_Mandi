from datetime import datetime,date,time
from flask import Blueprint,request,jsonify
from ..extensions import db
from ..models import *
from ..utils.security import role_required
from ..utils.audit import audit
admin_bp=Blueprint('admin',__name__)

@admin_bp.get('/stats')
@role_required(Role.ADMIN,Role.OFFICER)
def stats():
    return jsonify(success=True,data={'total_farmers':User.query.filter_by(role=Role.FARMER).count(),'verified_farmers':User.query.filter_by(role=Role.FARMER,verification_status=VerificationStatus.VERIFIED).count(),'pending_verification':User.query.filter_by(role=Role.FARMER,verification_status=VerificationStatus.PENDING).count(),'todays_bookings':Booking.query.join(ProcurementSlot).filter(ProcurementSlot.slot_date==date.today()).count(),'active_queues':QueueEntry.query.filter(QueueEntry.state.in_(['WAITING','PROCESSING'])).count(),'completed_procurements':ProcurementRecord.query.filter_by(status='COMPLETED').count(),'pending_payments':Payment.query.filter(Payment.status.in_([PaymentStatus.PENDING,PaymentStatus.PROCESSING])).count()})
@admin_bp.get('/farmers')
@role_required(Role.ADMIN,Role.OFFICER)
def farmers():
    page=max(int(request.args.get('page',1)),1); size=min(max(int(request.args.get('size',20)),1),100); q=User.query.filter_by(role=Role.FARMER).order_by(User.created_at.desc()); items=q.offset((page-1)*size).limit(size).all()
    return jsonify(success=True,data=[{'id':str(u.id),'public_id':u.public_id,'name':f'{u.first_name} {u.last_name}','mobile':u.mobile,'status':u.verification_status.value,'documents':[str(d.id) for d in u.documents]} for u in items],page=page,size=size,total=q.count())
@admin_bp.post('/farmers/<uuid:user_id>/approve')
@role_required(Role.ADMIN,Role.OFFICER)
def approve(user_id):
    u=User.query.get_or_404(user_id);u.verification_status=VerificationStatus.VERIFIED;u.farmer_profile.farmer_id=f'ACD-FR-{u.id.int%1000000:06d}'; FarmerDocument.query.filter_by(user_id=u.id,status='PENDING').update({'status':'APPROVED'});audit('FARMER_APPROVE','USER',u.id);db.session.commit();return jsonify(success=True,message='Farmer verified',farmer_id=u.farmer_profile.farmer_id)
@admin_bp.post('/farmers/<uuid:user_id>/reject')
@role_required(Role.ADMIN,Role.OFFICER)
def reject(user_id):
    u=User.query.get_or_404(user_id);u.verification_status=VerificationStatus.REJECTED;data=request.get_json() or {};FarmerDocument.query.filter_by(user_id=u.id,status='PENDING').update({'status':'REJECTED','remarks':data.get('remarks','')});audit('FARMER_REJECT','USER',u.id);db.session.commit();return jsonify(success=True,message='Farmer rejected')
@admin_bp.get('/procurement-centres')
@role_required(Role.ADMIN,Role.OFFICER)
def centres(): return jsonify(success=True,data=[{'id':str(c.id),'code':c.centre_code,'name':c.centre_name,'status':c.status,'capacity':c.daily_capacity} for c in ProcurementCentre.query.order_by(ProcurementCentre.centre_name).all()])
@admin_bp.post('/procurement-centres')
@role_required(Role.ADMIN)
def create_centre():
    d=request.get_json() or {}; c=ProcurementCentre(centre_code=d['centre_code'],centre_name=d['centre_name'],state_id=d['state_id'],district_id=d['district_id'],block_id=d['block_id'],address=d['address'],village=d.get('village'),pincode=d.get('pincode'),latitude=d.get('latitude'),longitude=d.get('longitude'),contact_number=d.get('contact_number'),operating_hours=d.get('operating_hours'),daily_capacity=d.get('daily_capacity',100));db.session.add(c);db.session.commit();return jsonify(success=True,data={'id':str(c.id)}),201
@admin_bp.post('/slots')
@role_required(Role.ADMIN)
def create_slots():
    d=request.get_json() or {}; s=ProcurementSlot(centre_id=d['centre_id'],crop_id=d['crop_id'],slot_date=date.fromisoformat(d['slot_date']),start_time=time.fromisoformat(d['start_time']),end_time=time.fromisoformat(d['end_time']),capacity=int(d.get('capacity',20)));db.session.add(s);db.session.commit();return jsonify(success=True,data={'id':str(s.id)}),201
@admin_bp.post('/bookings/<uuid:booking_id>/procurement')
@role_required(Role.ADMIN,Role.OFFICER)
def update_procurement(booking_id):
    b=Booking.query.get_or_404(booking_id);d=request.get_json() or {};p=b.procurement;p.status=d.get('status',p.status);p.quality_status=d.get('quality_status',p.quality_status);p.weight_kg=d.get('weight_kg',p.weight_kg);p.remarks=d.get('remarks',p.remarks)
    if p.status=='COMPLETED': b.status=BookingStatus.COMPLETED
    audit('PROCUREMENT_UPDATE','BOOKING',b.id);db.session.commit();return jsonify(success=True)
@admin_bp.post('/bookings/<uuid:booking_id>/payment')
@role_required(Role.ADMIN,Role.OFFICER)
def update_payment(booking_id):
    b=Booking.query.get_or_404(booking_id);d=request.get_json() or {};p=b.payment;p.status=PaymentStatus(d.get('status',p.status.value));p.amount=d.get('amount',p.amount);p.transaction_reference=d.get('transaction_reference',p.transaction_reference);p.completed_at=datetime.utcnow() if p.status==PaymentStatus.SUCCESS else p.completed_at;audit('PAYMENT_UPDATE','BOOKING',b.id);db.session.commit();return jsonify(success=True)
