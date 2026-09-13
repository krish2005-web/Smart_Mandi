import logging, requests
from flask import current_app
from ..extensions import db
from ..models import Notification
log=logging.getLogger(__name__)

def send_sms(mobile,message):
    provider=current_app.config.get('SMS_PROVIDER','console')
    if current_app.config.get('DEMO_MODE') or provider=='console':
        log.info('DEMO SMS to %s: %s',mobile,message); return True
    return False

def send_whatsapp(mobile,template_name,variables=None):
    token=current_app.config.get('WHATSAPP_ACCESS_TOKEN'); phone_id=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID')
    if current_app.config.get('DEMO_MODE') or not token or not phone_id:
        log.info('DEMO WhatsApp to %s template=%s vars=%s',mobile,template_name,variables); return True
    url=f'https://graph.facebook.com/v23.0/{phone_id}/messages'
    payload={'messaging_product':'whatsapp','to':mobile,'type':'template','template':{'name':template_name,'language':{'code':'en_IN'},'components':[]}}
    try:
        r=requests.post(url,json=payload,headers={'Authorization':f'Bearer {token}'},timeout=10); r.raise_for_status(); return True
    except Exception: log.exception('WhatsApp send failed'); return False

def notify_user(user_id,category,title_key,body_key,payload=None):
    db.session.add(Notification(user_id=user_id,category=category,title_key=title_key,body_key=body_key,payload=payload or {})); db.session.commit()
