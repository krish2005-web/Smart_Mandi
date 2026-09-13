from datetime import datetime
from secrets import token_urlsafe
from sqlalchemy import select
from ..extensions import db
from ..models import ProcurementSlot, Booking, BookingStatus, QueueEntry, ProcurementRecord, Payment, PaymentStatus

def create_booking(farmer, slot_id):
    with db.session.begin_nested():
        slot=db.session.execute(select(ProcurementSlot).where(ProcurementSlot.id==slot_id).with_for_update()).scalar_one_or_none()
        if not slot or slot.status!='OPEN' or slot.booked_count>=slot.capacity: raise ValueError('SLOT_FULL')
        duplicate=Booking.query.join(ProcurementSlot).filter(Booking.farmer_id==farmer.id,ProcurementSlot.slot_date==slot.slot_date,Booking.status.in_([BookingStatus.CONFIRMED,BookingStatus.PENDING,BookingStatus.CHECKED_IN,BookingStatus.IN_QUEUE,BookingStatus.PROCESSING])).first()
        if duplicate: raise ValueError('DUPLICATE_BOOKING')
        slot.booked_count+=1
        if slot.booked_count>=slot.capacity: slot.status='FULL'
        booking=Booking(booking_id=f'ACD-{datetime.utcnow().year}-{datetime.utcnow().strftime("%j%H%M%S")}-{token_urlsafe(3).upper()}',farmer_id=farmer.id,slot_id=slot.id,status=BookingStatus.CONFIRMED,qr_token=token_urlsafe(24))
        db.session.add(booking); db.session.flush()
        db.session.add(QueueEntry(booking_id=booking.id,state='WAITING'))
        db.session.add(ProcurementRecord(booking_id=booking.id,status='BOOKED'))
        db.session.add(Payment(payment_id=f'PAY-{token_urlsafe(7).upper()}',booking_id=booking.id,farmer_id=farmer.id,status=PaymentStatus.PENDING))
    db.session.commit(); return booking
