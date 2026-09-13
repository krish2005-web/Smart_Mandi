from datetime import date,time,timedelta
from app import create_app
from app.extensions import db
from app.models import *
app=create_app()
with app.app_context():
    db.create_all()
    states=['Andhra Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Odisha','Punjab','Rajasthan','Tamil Nadu','Telangana','Uttar Pradesh','Uttarakhand','West Bengal','Arunachal Pradesh','Manipur','Meghalaya','Mizoram','Nagaland','Sikkim','Tripura','Delhi','Jammu and Kashmir','Ladakh','Puducherry','Chandigarh','Andaman and Nicobar Islands','Dadra and Nagar Haveli and Daman and Diu','Lakshadweep']
    for name in states:
        if not State.query.filter_by(name=name).first(): db.session.add(State(name=name,lgd_code=f'SAMPLE-{name[:3].upper()}'))
    for name in ['Paddy/Rice','Wheat','Maize','Pulses','Oilseeds']:
        if not Crop.query.filter_by(name=name).first(): db.session.add(Crop(name=name))
    db.session.commit()
    s=State.query.filter_by(name='West Bengal').first(); d=District.query.filter_by(state_id=s.id).first()
    if not d:
        d=District(name='SAMPLE DISTRICT — replace with LGD import',state_id=s.id,lgd_code='SAMPLE-D1');db.session.add(d);db.session.flush()
    b=Block.query.filter_by(district_id=d.id).first()
    if not b:
        b=Block(name='SAMPLE BLOCK — replace with LGD import',district_id=d.id,lgd_code='SAMPLE-B1');db.session.add(b);db.session.flush()
    c=ProcurementCentre.query.filter_by(centre_code='DEMO-WB-001').first()
    if not c:
        c=ProcurementCentre(centre_code='DEMO-WB-001',centre_name='DEMO Procurement Centre',state_id=s.id,district_id=d.id,block_id=b.id,address='DEMO DATA — replace with official centre data',pincode='700000',latitude=22.5726,longitude=88.3639,daily_capacity=100);db.session.add(c);db.session.flush()
    crop=Crop.query.filter_by(name='Paddy/Rice').first()
    for i in range(3):
        sd=date.today()+timedelta(days=i+1)
        for h in [9,10,11,14,15]:
            if not ProcurementSlot.query.filter_by(centre_id=c.id,crop_id=crop.id,slot_date=sd,start_time=time(h)).first(): db.session.add(ProcurementSlot(centre_id=c.id,crop_id=crop.id,slot_date=sd,start_time=time(h),end_time=time(h+1),capacity=20))
    admin=User.query.filter_by(mobile='9000000001').first()
    if not admin:
        admin=User(first_name='Demo',last_name='Admin',mobile='9000000001',role=Role.ADMIN,preferred_language='en',verification_status=VerificationStatus.VERIFIED);admin.set_password('Admin@12345');db.session.add(admin)
    op=User.query.filter_by(mobile='9000000002').first()
    if not op:
        op=User(first_name='Demo',last_name='Operator',mobile='9000000002',role=Role.OPERATOR,preferred_language='en',verification_status=VerificationStatus.VERIFIED);op.set_password('Operator@12345');db.session.add(op);db.session.flush();db.session.add(OperatorAssignment(operator_id=op.id,centre_id=c.id))
    db.session.commit();print('Seed complete. DEMO DATA is clearly marked and must be replaced/imported from authoritative datasets.')
