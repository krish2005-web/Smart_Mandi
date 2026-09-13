import requests
from flask import current_app
from ..models import Booking, QueueEntry, Payment, ProcurementRecord

def tools_for_user(user):
    def get_my_booking():
        b=Booking.query.filter_by(farmer_id=user.id).order_by(Booking.created_at.desc()).first()
        if not b: return {'booking':None}
        return {'booking_id':b.booking_id,'status':b.status.value,'date':b.slot.slot_date.isoformat(),'start':b.slot.start_time.strftime('%H:%M'),'centre':b.slot.centre.centre_name}
    def get_queue_status():
        b=Booking.query.filter_by(farmer_id=user.id).order_by(Booking.created_at.desc()).first(); q=b.queue_entry if b else None
        return {'position':q.position,'estimated_minutes':q.estimated_minutes,'state':q.state} if q else {'position':None}
    def get_procurement_status():
        b=Booking.query.filter_by(farmer_id=user.id).order_by(Booking.created_at.desc()).first(); p=b.procurement if b else None
        return {'status':p.status if p else None,'weight_kg':float(p.weight_kg) if p and p.weight_kg else None,'quality':p.quality_status if p else None}
    def get_payment_status():
        b=Booking.query.filter_by(farmer_id=user.id).order_by(Booking.created_at.desc()).first(); p=b.payment if b else None
        return {'status':p.status.value if p else None,'amount':float(p.amount) if p else None}
    return {'booking':get_my_booking,'queue':get_queue_status,'procurement':get_procurement_status,'payment':get_payment_status}

def answer(user,message):
    low=message.lower(); tools=tools_for_user(user)
    if any(x in low for x in ['my booking','booking','slot']): data=tools['booking']()
    elif 'queue' in low or 'waiting' in low: data=tools['queue']()
    elif 'payment' in low: data=tools['payment']()
    elif 'procurement' in low or 'status' in low: data=tools['procurement']()
    else: data={'help':'Ask about booking, queue, procurement status, payment, documents, or how to use SmartMandi.'}
    key=current_app.config.get('GEMINI_API_KEY')
    if not key: return {'reply':fallback(data), 'source':'fallback'}
    prompt=f'You are SmartMandi farmer assistant. Answer only from the authenticated data and general help. User language: {user.preferred_language}. Do not invent private facts. Data: {data}. Question: {message}'
    try:
        url=f'https://generativelanguage.googleapis.com/v1beta/models/{current_app.config.get("GEMINI_MODEL")}:generateContent?key={key}'
        r=requests.post(url,json={'contents':[{'parts':[{'text':prompt}]}]},timeout=15); r.raise_for_status()
        txt=r.json()['candidates'][0]['content']['parts'][0]['text']; return {'reply':txt,'source':'gemini'}
    except Exception: return {'reply':fallback(data),'source':'fallback'}

def fallback(data):
    if 'booking_id' in data: return f"Your latest booking is {data['booking_id']} at {data['centre']} on {data['date']} from {data['start']}. Status: {data['status']}."
    if 'position' in data: return f"Your queue position is {data['position'] or 'not assigned yet'}, with an estimated wait of {data['estimated_minutes'] or 0} minutes."
    if 'amount' in data: return f"Payment status: {data['status'] or 'not available'}. Amount: ₹{data['amount'] or 0:.2f}."
    if 'status' in data: return f"Procurement status: {data['status'] or 'not available'}."
    return data['help']
