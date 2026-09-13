from datetime import datetime, timedelta
import re, os, uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies, jwt_required, get_jwt_identity
from ..extensions import db, limiter
from ..models import User, FarmerProfile, Address, State, District, Block, Panchayat, Village, PoliceStation, PostOffice, Pincode, FarmerDocument, VerificationStatus, Role
from ..services.otp_service import issue_otp, verify_otp
from ..utils.audit import audit

auth_bp=Blueprint('auth',__name__)
PASSWORD=re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,}$')

def validate(data):
    required=['first_name','last_name','mobile','password','confirm_password','preferred_language','state_id','district_id','block_id','line1']
    missing=[x for x in required if not data.get(x)]
    if missing: return 'Missing required fields'
    if not re.fullmatch(r'[6-9]\d{9}',str(data['mobile'])): return 'Invalid Indian mobile number'
    if data['password']!=data['confirm_password'] or not PASSWORD.match(data['password']): return 'Password does not meet strength requirements'
    return None

@auth_bp.post('/register')
@limiter.limit('5 per minute')
def register():
    data=request.form.to_dict() if request.form else request.get_json(silent=True) or {}
    err=validate(data)
    if err: return jsonify(success=False,message=err,error_code='VALIDATION_ERROR'),400
    if User.query.filter_by(mobile=data['mobile']).first(): return jsonify(success=False,message='Mobile already registered',error_code='MOBILE_EXISTS'),409
    ids=['state_id','district_id','block_id','panchayat_id','village_id','police_station_id','post_office_id','pincode_id']
    models=[State,District,Block,Panchayat,Village,PoliceStation,PostOffice,Pincode]
    for key,model in zip(ids,models):
        if data.get(key) and not model.query.get(int(data[key])): return jsonify(success=False,message=f'Invalid {key}',error_code='INVALID_REFERENCE'),400
    user=User(first_name=data['first_name'].strip(),last_name=data['last_name'].strip(),mobile=data['mobile'],email=data.get('email') or None,preferred_language=data.get('preferred_language','en'),role=Role.FARMER,verification_status=VerificationStatus.DOCUMENT_REQUIRED)
    user.set_password(data['password']); db.session.add(user); db.session.flush()
    address=Address(state_id=int(data['state_id']),district_id=int(data['district_id']),block_id=int(data['block_id']),panchayat_id=int(data['panchayat_id']) if data.get('panchayat_id') else None,village_id=int(data['village_id']) if data.get('village_id') else None,police_station_id=int(data['police_station_id']) if data.get('police_station_id') else None,post_office_id=int(data['post_office_id']) if data.get('post_office_id') else None,pincode_id=int(data['pincode_id']) if data.get('pincode_id') else None,line1=data['line1'].strip())
    db.session.add(address); db.session.flush(); db.session.add(FarmerProfile(user_id=user.id,address_id=address.id)); db.session.commit()
    issue_otp(user.mobile,'REGISTRATION'); audit('REGISTER','USER',user.id); db.session.commit()
    return jsonify(success=True,message='Registration created. Verify OTP and submit farmer proof.',user_id=str(user.id),verification_status=user.verification_status.value),201

@auth_bp.post('/verify-otp')
@limiter.limit('10 per minute')
def verify():
    data=request.get_json() or {}
    if not verify_otp(data.get('mobile',''),data.get('code',''),data.get('purpose','REGISTRATION')): return jsonify(success=False,message='Invalid or expired OTP',error_code='OTP_INVALID'),400
    return jsonify(success=True,message='Mobile verified')

@auth_bp.post('/login')
@limiter.limit('10 per minute')
def login():
    data=request.get_json() or {}; identifier=data.get('identifier','').strip(); password=data.get('password','')
    user=User.query.filter((User.mobile==identifier)|(User.public_id==identifier)).first()
    if not user or not user.check_password(password) or not user.is_active: return jsonify(success=False,message='Invalid credentials',error_code='AUTH_FAILED'),401
    if user.role==Role.FARMER and user.verification_status!=VerificationStatus.VERIFIED: return jsonify(success=False,message='Farmer verification is not complete',error_code='NOT_VERIFIED'),403
    token=create_access_token(identity=str(user.id),additional_claims={'role':user.role.value,'public_id':user.public_id},expires_delta=timedelta(hours=4)); resp=jsonify(success=True,user={'id':str(user.id),'public_id':user.public_id,'name':f'{user.first_name} {user.last_name}','role':user.role.value,'language':user.preferred_language}); set_access_cookies(resp,token); return resp

@auth_bp.post('/logout')
def logout():
    resp=jsonify(success=True,message='Logged out'); unset_jwt_cookies(resp); return resp

@auth_bp.get('/me')
@jwt_required()
def me():
    user=User.query.get(get_jwt_identity()); return jsonify(success=True,user={'id':str(user.id),'public_id':user.public_id,'name':f'{user.first_name} {user.last_name}','role':user.role.value,'language':user.preferred_language,'verification_status':user.verification_status.value})

@auth_bp.post('/forgot-password')
def forgot():
    data=request.get_json() or {}; user=User.query.filter_by(mobile=data.get('mobile')).first()
    if user: issue_otp(user.mobile,'PASSWORD_RESET')
    return jsonify(success=True,message='If the account exists, a reset OTP has been issued.')

@auth_bp.post('/reset-password')
def reset():
    data=request.get_json() or {}; user=User.query.filter_by(mobile=data.get('mobile')).first()
    if not user or not verify_otp(data.get('mobile'),data.get('otp'),'PASSWORD_RESET') or not PASSWORD.match(data.get('password','')): return jsonify(success=False,message='Unable to reset password',error_code='RESET_FAILED'),400
    user.set_password(data['password']); db.session.commit(); return jsonify(success=True,message='Password reset successfully')
