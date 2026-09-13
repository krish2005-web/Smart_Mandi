from datetime import datetime, date, time
from math import radians,sin,cos,asin,sqrt
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import *
from ..utils.security import current_user, role_required
from ..utils.audit import audit
from ..services.booking_service import create_booking
from ..services.notification_service import notify_user, send_sms, send_whatsapp

api_bp=Blueprint('api',__name__)
ALLOWED={'pdf','jpg','jpeg','png'}

def rows(query): return [{'id':r.id,'name':r.name} for r in query.order_by(db.func.lower(query.column_descriptions[0]['expr'].name)).all()]

@api_bp.get('/states')
def states(): return jsonify(success=True,data=[{'id':x.id,'name':x.name,'lgd_code':x.lgd_code} for x in State.query.order_by(State.name).all()])
@api_bp.get('/districts/<int:state_id>')
def districts(state_id): return jsonify(success=True,data=[{'id':x.id,'name':x.name,'lgd_code':x.lgd_code} for x in District.query.filter_by(state_id=state_id).order_by(District.name).all()])
@api_bp.get('/blocks/<int:district_id>')
def blocks(district_id): return jsonify(success=True,data=[{'id':x.id,'name':x.name,'lgd_code':x.lgd_code} for x in Block.query.filter_by(district_id=district_id).order_by(Block.name).all()])
@api_bp.get('/panchayats/<int:block_id>')
def panchayats(block_id): return jsonify(success=True,data=[{'id':x.id,'name':x.name,'lgd_code':x.lgd_code} for x in Panchayat.query.filter_by(block_id=block_id).order_by(Panchayat.name).all()])
@api_bp.get('/villages/<int:panchayat_id>')
def villages(panchayat_id): return jsonify(success=True,data=[{'id':x.id,'name':x.name,'lgd_code':x.lgd_code,'pincode':x.pincode} for x in Village.query.filter_by(panchayat_id=panchayat_id).order_by(Village.name).all()])
@api_bp.get('/police-stations/<int:district_id>')
def police_stations(district_id): return jsonify(success=True,data=[{'id':x.id,'name':x.name} for x in PoliceStation.query.filter_by(district_id=district_id).order_by(PoliceStation.name).all()])
@api_bp.get('/post-offices/<int:district_id>')
def post_offices(district_id): return jsonify(success=True,data=[{'id':x.id,'name':x.name,'pincode':x.pincode} for x in PostOffice.query.filter_by(district_id=district_id).order_by(PostOffice.name).all()])
@api_bp.get('/pincodes')
def pincodes(): return jsonify(success=True,data=[{'id':x.id,'pincode':x.pincode} for x in Pincode.query.order_by(Pincode.pincode).all()][:500])

@api_bp.post('/farmer/document')
@jwt_required()
def upload_document():
    user=current_user(); f=request.files.get('document'); dtype=request.form.get('document_type','FARMER_PROOF')
    if not f or not f.filename: return jsonify(success=False,message='Document is required',error_code='DOCUMENT_REQUIRED'),400
    ext=f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED or f.mimetype not in {'application/pdf','image/jpeg','image/png'}: return jsonify(success=False,message='Unsupported file type',error_code='INVALID_FILE'),400
    name=f'{user.id.hex}_{__import__("secrets").token_hex(16)}.{ext}'; path=__import__('os').path.join(current_app.config['UPLOAD_DIR'],name); f.save(path)
    doc=FarmerDocument(user_id=user.id,document_type=dtype,original_name=secure_filename(f.filename)[:255],stored_name=name,mime_type=f.mimetype,size_bytes=__import__('os').path.getsize(path)); db.session.add(doc); user.verification_status=VerificationStatus.PENDING; audit('DOCUMENT_UPLOAD','FARMER_DOCUMENT',doc.id); db.session.commit()
    return jsonify(success=True,message='Document uploaded and sent for verification')

@api_bp.get('/farmer/document/<uuid:doc_id>')
@role_required(Role.ADMIN,Role.OFFICER)
def private_document(doc_id):
    doc=FarmerDocument.query.get_or_404(doc_id); import os
    return send_file(os.path.join(current_app.config['UPLOAD_DIR'],doc.stored_name),download_name=doc.original_name,mimetype=doc.mime_type,as_attachment=True)

@api_bp.get('/crops')
def crops(): return jsonify(success=True,data=[{'id':x.id,'name':x.name} for x in Crop.query.filter_by(active=True).order_by(Crop.name).all()])
@api_bp.get('/procurement-centres')
def centres():
    q=ProcurementCentre.query.filter_by(status='ACTIVE')
    for key in ('state_id','district_id','block_id'):
        if request.args.get(key): q=q.filter(getattr(ProcurementCentre,key)==int(request.args[key]))
    return jsonify(success=True,data=[{'id':str(x.id),'code':x.centre_code,'name':x.centre_name,'address':x.address,'pincode':x.pincode,'lat':float(x.latitude) if x.latitude else None,'lng':float(x.longitude) if x.longitude else None,'capacity':x.daily_capacity} for x in q.order_by(ProcurementCentre.centre_name).limit(100).all()])
@api_bp.get('/procurement-centres/nearest')
def nearest():
    try: lat=float(request.args['lat']); lng=float(request.args['lng'])
    except Exception: return jsonify(success=False,message='Valid lat/lng required',error_code='INVALID_LOCATION'),400
    def dist(c):
        if c.latitude is None or c.longitude is None:return 10**9
        p1,p2=radians(lat),radians(float(c.latitude)); dlat=radians(float(c.latitude)-lat);dlon=radians(float(c.longitude)-lng);a=sin(dlat/2)**2+cos(p1)*cos(p2)*sin(dlon/2)**2;return 6371*2*asin(sqrt(a))
    data=[]
    for c in ProcurementCentre.query.filter_by(status='ACTIVE').all(): data.append((dist(c),c))
    data.sort(key=lambda z:z[0]); return jsonify(success=True,data=[{'id':str(c.id),'name':c.centre_name,'distance_km':round(d,2),'address':c.address} for d,c in data[:10]])

@api_bp.get('/slots')
def slots():
    q=ProcurementSlot.query.filter_by(status='OPEN').filter(ProcurementSlot.slot_date>=date.today())
    for key in ('centre_id','crop_id','slot_date'):
        if request.args.get(key): q=q.filter(getattr(ProcurementSlot,key)==(request.args[key] if key!='crop_id' else int(request.args[key])))
    return jsonify(success=True,data=[{'id':str(s.id),'date':s.slot_date.isoformat(),'start':s.start_time.strftime('%H:%M'),'end':s.end_time.strftime('%H:%M'),'capacity':s.capacity,'available':s.capacity-s.booked_count,'crop':s.crop.name} for s in q.order_by(ProcurementSlot.slot_date,ProcurementSlot.start_time).limit(200).all()])

@api_bp.post('/bookings')
@jwt_required()
def bookings_create():
    user=current_user()
    if user.role!=Role.FARMER or user.verification_status!=VerificationStatus.VERIFIED: return jsonify(success=False,message='Verified farmer account required',error_code='NOT_VERIFIED'),403
    data=request.get_json() or {}
    try: b=create_booking(user,data['slot_id'])
    except KeyError: return jsonify(success=False,message='slot_id is required',error_code='VALIDATION_ERROR'),400
    except ValueError as e: return jsonify(success=False,message='Unable to book slot',error_code=str(e)),409
    notify_user(user.id,'BOOKING','booking.confirmed','booking.confirmed_body',{'booking_id':b.booking_id}); send_sms(user.mobile,f'SmartMandi booking confirmed: {b.booking_id}'); send_whatsapp(user.mobile,'booking_confirmation',[b.booking_id]); audit('BOOKING_CREATE','BOOKING',b.id); db.session.commit()
    return jsonify(success=True,data={'booking_id':b.booking_id,'id':str(b.id),'status':b.status.value}),201

@api_bp.get('/bookings/my')
@jwt_required()
def my_bookings():
    user=current_user(); data=[]
    for b in Booking.query.filter_by(farmer_id=user.id).order_by(Booking.created_at.desc()).limit(50).all(): data.append(booking_payload(b))
    return jsonify(success=True,data=data)

def booking_payload(b):
    return {'id':str(b.id),'booking_id':b.booking_id,'status':b.status.value,'centre':b.slot.centre.centre_name,'date':b.slot.slot_date.isoformat(),'start':b.slot.start_time.strftime('%H:%M'),'end':b.slot.end_time.strftime('%H:%M'),'crop':b.slot.crop.name,'queue':{'position':b.queue_entry.position,'estimated_minutes':b.queue_entry.estimated_minutes,'state':b.queue_entry.state} if b.queue_entry else None,'procurement':{'status':b.procurement.status,'quality':b.procurement.quality_status,'weight_kg':float(b.procurement.weight_kg) if b.procurement and b.procurement.weight_kg else None} if b.procurement else None,'payment':{'payment_id':b.payment.payment_id,'status':b.payment.status.value,'amount':float(b.payment.amount)} if b.payment else None}

@api_bp.get('/bookings/<uuid:booking_id>')
@jwt_required()
def booking_detail(booking_id):
    b=Booking.query.get_or_404(booking_id); u=current_user()
    if u.role==Role.FARMER and b.farmer_id!=u.id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    return jsonify(success=True,data=booking_payload(b))
@api_bp.post('/bookings/<uuid:booking_id>/cancel')
@jwt_required()
def booking_cancel(booking_id):
    b=Booking.query.get_or_404(booking_id); u=current_user()
    if u.role==Role.FARMER and b.farmer_id!=u.id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    if b.status not in [BookingStatus.CONFIRMED,BookingStatus.PENDING]: return jsonify(success=False,message='Booking cannot be cancelled now',error_code='INVALID_STATUS'),409
    b.status=BookingStatus.CANCELLED; b.slot.booked_count=max(0,b.slot.booked_count-1); b.slot.status='OPEN'; audit('BOOKING_CANCEL','BOOKING',b.id); db.session.commit(); return jsonify(success=True,message='Booking cancelled')

@api_bp.get('/queue/<uuid:booking_id>')
@jwt_required()
def queue(booking_id):
    b=Booking.query.get_or_404(booking_id); u=current_user()
    if u.role==Role.FARMER and b.farmer_id!=u.id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    return jsonify(success=True,data={'token':b.queue_entry.token_number,'position':b.queue_entry.position,'estimated_minutes':b.queue_entry.estimated_minutes,'state':b.queue_entry.state,'counter':b.queue_entry.counter})
@api_bp.get('/procurement/<uuid:booking_id>')
@jwt_required()
def procurement(booking_id):
    b=Booking.query.get_or_404(booking_id);u=current_user()
    if u.role==Role.FARMER and b.farmer_id!=u.id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    return jsonify(success=True,data=booking_payload(b)['procurement'])
@api_bp.get('/payment/<uuid:booking_id>')
@jwt_required()
def payment(booking_id):
    b=Booking.query.get_or_404(booking_id);u=current_user()
    if u.role==Role.FARMER and b.farmer_id!=u.id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    return jsonify(success=True,data=booking_payload(b)['payment'])
@api_bp.get('/notifications')
@jwt_required()
def notifications():
    u=current_user(); return jsonify(success=True,data=[{'id':str(n.id),'category':n.category,'title_key':n.title_key,'body_key':n.body_key,'payload':n.payload,'read':bool(n.read_at),'created_at':n.created_at.isoformat()} for n in Notification.query.filter_by(user_id=u.id).order_by(Notification.created_at.desc()).limit(100).all()])
@api_bp.post('/notifications/<uuid:notification_id>/read')
@jwt_required()
def notification_read(notification_id):
    n=Notification.query.get_or_404(notification_id);u=current_user()
    if n.user_id!=u.id:return jsonify(success=False,message='Forbidden',error_code='FORBIDDEN'),403
    n.read_at=datetime.utcnow();db.session.commit();return jsonify(success=True)
