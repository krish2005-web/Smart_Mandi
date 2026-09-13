from datetime import datetime, timedelta
from secrets import randbelow
from argon2 import PasswordHasher
from ..extensions import db
from ..models import OTPVerification
from .notification_service import send_sms
ph=PasswordHasher()

def issue_otp(mobile,purpose='REGISTRATION'):
    code=f'{randbelow(900000)+100000}'
    row=OTPVerification(mobile=mobile,purpose=purpose,code_hash=ph.hash(code),expires_at=datetime.utcnow()+timedelta(minutes=5))
    db.session.add(row); db.session.commit()
    send_sms(mobile, f'SmartMandi OTP for {purpose}: {code}')
    return code

def verify_otp(mobile, code, purpose):
    row=OTPVerification.query.filter_by(mobile=mobile,purpose=purpose,verified_at=None).order_by(OTPVerification.created_at.desc()).first()
    if not row or row.expires_at < datetime.utcnow() or row.attempts >= 5: return False
    row.attempts += 1
    try: ok=ph.verify(row.code_hash, code)
    except Exception: ok=False
    if ok: row.verified_at=datetime.utcnow()
    db.session.commit(); return ok
