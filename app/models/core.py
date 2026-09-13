from datetime import datetime
from uuid import uuid4
from enum import Enum
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from ..extensions import db

ph = PasswordHasher()

def public_id(prefix):
    return f'{prefix}-{uuid4().hex[:12].upper()}'

class Role(str, Enum):
    FARMER='FARMER'; OPERATOR='OPERATOR'; ADMIN='ADMIN'; OFFICER='OFFICER'
class VerificationStatus(str, Enum):
    PENDING='PENDING_VERIFICATION'; VERIFIED='VERIFIED'; REJECTED='REJECTED'; DOCUMENT_REQUIRED='DOCUMENT_REQUIRED'
class BookingStatus(str, Enum):
    PENDING='PENDING'; CONFIRMED='CONFIRMED'; CHECKED_IN='CHECKED_IN'; IN_QUEUE='IN_QUEUE'; PROCESSING='PROCESSING'; COMPLETED='COMPLETED'; CANCELLED='CANCELLED'; NO_SHOW='NO_SHOW'
class PaymentStatus(str, Enum):
    PENDING='PENDING'; PROCESSING='PROCESSING'; SUCCESS='SUCCESS'; FAILED='FAILED'

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class User(TimestampMixin, db.Model):
    __tablename__='users'
    id=db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4)
    public_id=db.Column(db.String(32), unique=True, nullable=False, default=lambda: public_id('ACD'))
    first_name=db.Column(db.String(80), nullable=False)
    last_name=db.Column(db.String(80), nullable=False)
    mobile=db.Column(db.String(10), unique=True, nullable=False, index=True)
    email=db.Column(db.String(255), unique=True, nullable=True)
    dob=db.Column(db.Date, nullable=True)
    gender=db.Column(db.String(30), nullable=True)
    password_hash=db.Column(db.String(512), nullable=False)
    role=db.Column(db.Enum(Role, name='role_enum'), nullable=False, default=Role.FARMER)
    preferred_language=db.Column(db.String(10), nullable=False, default='en')
    verification_status=db.Column(db.Enum(VerificationStatus, name='verification_status_enum'), nullable=False, default=VerificationStatus.DOCUMENT_REQUIRED)
    failed_login_attempts=db.Column(db.Integer, default=0, nullable=False)
    locked_until=db.Column(db.DateTime, nullable=True)
    is_active=db.Column(db.Boolean, default=True, nullable=False)
    farmer_profile=db.relationship('FarmerProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    documents=db.relationship('FarmerDocument', back_populates='user', cascade='all, delete-orphan')
    def set_password(self, password): self.password_hash=ph.hash(password)
    def check_password(self, password):
        try: return ph.verify(self.password_hash, password)
        except VerifyMismatchError: return False

class FarmerProfile(TimestampMixin, db.Model):
    __tablename__='farmer_profiles'
    id=db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id=db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    farmer_id=db.Column(db.String(24), unique=True, nullable=True)
    address_id=db.Column(db.UUID(as_uuid=True), db.ForeignKey('addresses.id'), nullable=True)
    user=db.relationship('User', back_populates='farmer_profile')
    address=db.relationship('Address')

class State(TimestampMixin, db.Model):
    __tablename__='states'; id=db.Column(db.Integer, primary_key=True); lgd_code=db.Column(db.String(20), unique=True); name=db.Column(db.String(100), unique=True, nullable=False); districts=db.relationship('District', back_populates='state')
class District(TimestampMixin, db.Model):
    __tablename__='districts'; id=db.Column(db.Integer, primary_key=True); lgd_code=db.Column(db.String(20), unique=True); name=db.Column(db.String(100), nullable=False); state_id=db.Column(db.Integer, db.ForeignKey('states.id'), nullable=False, index=True); state=db.relationship('State', back_populates='districts'); blocks=db.relationship('Block', back_populates='district')
    __table_args__=(db.UniqueConstraint('state_id','name',name='uq_district_state_name'),)
class Block(TimestampMixin, db.Model):
    __tablename__='blocks'; id=db.Column(db.Integer, primary_key=True); lgd_code=db.Column(db.String(20), unique=True); name=db.Column(db.String(120), nullable=False); district_id=db.Column(db.Integer, db.ForeignKey('districts.id'), nullable=False, index=True); district=db.relationship('District', back_populates='blocks'); panchayats=db.relationship('Panchayat', back_populates='block')
    __table_args__=(db.UniqueConstraint('district_id','name',name='uq_block_district_name'),)
class Panchayat(TimestampMixin, db.Model):
    __tablename__='panchayats'; id=db.Column(db.Integer, primary_key=True); lgd_code=db.Column(db.String(20), unique=True); name=db.Column(db.String(150), nullable=False); block_id=db.Column(db.Integer, db.ForeignKey('blocks.id'), nullable=False, index=True); block=db.relationship('Block', back_populates='panchayats'); villages=db.relationship('Village', back_populates='panchayat')
class Village(TimestampMixin, db.Model):
    __tablename__='villages'; id=db.Column(db.Integer, primary_key=True); lgd_code=db.Column(db.String(20), unique=True); name=db.Column(db.String(180), nullable=False); panchayat_id=db.Column(db.Integer, db.ForeignKey('panchayats.id'), nullable=False, index=True); panchayat=db.relationship('Panchayat', back_populates='villages'); pincode=db.Column(db.String(6))
class PoliceStation(TimestampMixin, db.Model):
    __tablename__='police_stations'; id=db.Column(db.Integer, primary_key=True); name=db.Column(db.String(150), nullable=False); district_id=db.Column(db.Integer, db.ForeignKey('districts.id'), nullable=False, index=True)
class PostOffice(TimestampMixin, db.Model):
    __tablename__='post_offices'; id=db.Column(db.Integer, primary_key=True); name=db.Column(db.String(150), nullable=False); district_id=db.Column(db.Integer, db.ForeignKey('districts.id'), nullable=False, index=True); pincode=db.Column(db.String(6), nullable=False, index=True)
class Pincode(TimestampMixin, db.Model):
    __tablename__='pincodes'; id=db.Column(db.Integer, primary_key=True); pincode=db.Column(db.String(6), unique=True, nullable=False, index=True); state_id=db.Column(db.Integer, db.ForeignKey('states.id'), nullable=False)
class Address(TimestampMixin, db.Model):
    __tablename__='addresses'; id=db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4); state_id=db.Column(db.Integer, db.ForeignKey('states.id'), nullable=False); district_id=db.Column(db.Integer, db.ForeignKey('districts.id'), nullable=False); block_id=db.Column(db.Integer, db.ForeignKey('blocks.id'), nullable=False); panchayat_id=db.Column(db.Integer, db.ForeignKey('panchayats.id'), nullable=True); village_id=db.Column(db.Integer, db.ForeignKey('villages.id'), nullable=True); police_station_id=db.Column(db.Integer, db.ForeignKey('police_stations.id'), nullable=True); post_office_id=db.Column(db.Integer, db.ForeignKey('post_offices.id'), nullable=True); pincode_id=db.Column(db.Integer, db.ForeignKey('pincodes.id'), nullable=True); line1=db.Column(db.String(255), nullable=False)

class FarmerDocument(TimestampMixin, db.Model):
    __tablename__='farmer_documents'
    id=db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid4); user_id=db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id',ondelete='CASCADE'),nullable=False,index=True); document_type=db.Column(db.String(80),nullable=False); original_name=db.Column(db.String(255),nullable=False); stored_name=db.Column(db.String(255),nullable=False,unique=True); mime_type=db.Column(db.String(100),nullable=False); size_bytes=db.Column(db.Integer,nullable=False); status=db.Column(db.String(30),default='PENDING',nullable=False); remarks=db.Column(db.String(500)); user=db.relationship('User',back_populates='documents')
class OTPVerification(TimestampMixin, db.Model):
    __tablename__='otp_verifications'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); mobile=db.Column(db.String(10),nullable=False,index=True); purpose=db.Column(db.String(30),nullable=False); code_hash=db.Column(db.String(512),nullable=False); expires_at=db.Column(db.DateTime,nullable=False); attempts=db.Column(db.Integer,default=0,nullable=False); verified_at=db.Column(db.DateTime)
class ProcurementCentre(TimestampMixin, db.Model):
    __tablename__='procurement_centres'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); centre_code=db.Column(db.String(40),unique=True,nullable=False); centre_name=db.Column(db.String(180),nullable=False); state_id=db.Column(db.Integer,db.ForeignKey('states.id'),nullable=False,index=True); district_id=db.Column(db.Integer,db.ForeignKey('districts.id'),nullable=False,index=True); block_id=db.Column(db.Integer,db.ForeignKey('blocks.id'),nullable=False,index=True); address=db.Column(db.String(255),nullable=False); village=db.Column(db.String(150)); pincode=db.Column(db.String(6)); latitude=db.Column(db.Numeric(9,6)); longitude=db.Column(db.Numeric(9,6)); contact_number=db.Column(db.String(15)); operating_hours=db.Column(db.String(100)); daily_capacity=db.Column(db.Integer,default=100,nullable=False); status=db.Column(db.String(20),default='ACTIVE',nullable=False); slots=db.relationship('ProcurementSlot',back_populates='centre',cascade='all,delete-orphan')
class Crop(TimestampMixin, db.Model):
    __tablename__='crops'; id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(100),unique=True,nullable=False); active=db.Column(db.Boolean,default=True,nullable=False); notes=db.Column(db.String(255))
class ProcurementSlot(TimestampMixin, db.Model):
    __tablename__='procurement_slots'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); centre_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('procurement_centres.id',ondelete='CASCADE'),nullable=False,index=True); crop_id=db.Column(db.Integer,db.ForeignKey('crops.id'),nullable=False); slot_date=db.Column(db.Date,nullable=False,index=True); start_time=db.Column(db.Time,nullable=False); end_time=db.Column(db.Time,nullable=False); capacity=db.Column(db.Integer,nullable=False); booked_count=db.Column(db.Integer,default=0,nullable=False); status=db.Column(db.String(20),default='OPEN',nullable=False); centre=db.relationship('ProcurementCentre',back_populates='slots'); crop=db.relationship('Crop'); bookings=db.relationship('Booking',back_populates='slot')
    __table_args__=(db.UniqueConstraint('centre_id','crop_id','slot_date','start_time',name='uq_slot'),)
class Booking(TimestampMixin, db.Model):
    __tablename__='bookings'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); booking_id=db.Column(db.String(32),unique=True,nullable=False); farmer_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('users.id'),nullable=False,index=True); slot_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('procurement_slots.id'),nullable=False,index=True); status=db.Column(db.Enum(BookingStatus,name='booking_status_enum'),default=BookingStatus.CONFIRMED,nullable=False); qr_token=db.Column(db.String(64),unique=True,nullable=False); slot=db.relationship('ProcurementSlot',back_populates='bookings'); farmer=db.relationship('User'); queue_entry=db.relationship('QueueEntry',back_populates='booking',uselist=False,cascade='all,delete-orphan'); procurement=db.relationship('ProcurementRecord',back_populates='booking',uselist=False,cascade='all,delete-orphan'); payment=db.relationship('Payment',back_populates='booking',uselist=False,cascade='all,delete-orphan')
class QueueEntry(TimestampMixin, db.Model):
    __tablename__='queue_entries'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); booking_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('bookings.id',ondelete='CASCADE'),unique=True,nullable=False); token_number=db.Column(db.Integer,nullable=True); position=db.Column(db.Integer,nullable=True); estimated_minutes=db.Column(db.Integer,default=0); counter=db.Column(db.String(30)); state=db.Column(db.String(30),default='WAITING'); checked_in_at=db.Column(db.DateTime); called_at=db.Column(db.DateTime); booking=db.relationship('Booking',back_populates='queue_entry')
class ProcurementRecord(TimestampMixin, db.Model):
    __tablename__='procurement_records'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); booking_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('bookings.id',ondelete='CASCADE'),unique=True,nullable=False); quality_status=db.Column(db.String(30)); weight_kg=db.Column(db.Numeric(12,2)); status=db.Column(db.String(30),default='BOOKED',nullable=False); remarks=db.Column(db.String(500)); booking=db.relationship('Booking',back_populates='procurement')
class Payment(TimestampMixin, db.Model):
    __tablename__='payments'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); payment_id=db.Column(db.String(32),unique=True,nullable=False); booking_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('bookings.id',ondelete='CASCADE'),unique=True,nullable=False); farmer_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('users.id'),nullable=False); amount=db.Column(db.Numeric(12,2),default=0); status=db.Column(db.Enum(PaymentStatus,name='payment_status_enum'),default=PaymentStatus.PENDING); transaction_reference=db.Column(db.String(100)); initiated_at=db.Column(db.DateTime); completed_at=db.Column(db.DateTime); booking=db.relationship('Booking',back_populates='payment')
class Notification(TimestampMixin, db.Model):
    __tablename__='notifications'; id=db.Column(db.UUID(as_uuid=True),primary_key=True,default=uuid4); user_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('users.id',ondelete='CASCADE'),nullable=False,index=True); category=db.Column(db.String(40),nullable=False); title_key=db.Column(db.String(120),nullable=False); body_key=db.Column(db.String(120),nullable=False); payload=db.Column(db.JSON,default=dict); read_at=db.Column(db.DateTime)
class AuditLog(db.Model):
    __tablename__='audit_logs'; id=db.Column(db.BigInteger,primary_key=True); actor_user_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('users.id'),nullable=True,index=True); action=db.Column(db.String(80),nullable=False); resource=db.Column(db.String(80),nullable=False); resource_id=db.Column(db.String(120)); ip_address=db.Column(db.String(64)); user_agent=db.Column(db.String(512)); created_at=db.Column(db.DateTime,default=datetime.utcnow,nullable=False,index=True)
class OperatorAssignment(db.Model):
    __tablename__='operator_assignments'; id=db.Column(db.Integer,primary_key=True); operator_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('users.id',ondelete='CASCADE'),nullable=False); centre_id=db.Column(db.UUID(as_uuid=True),db.ForeignKey('procurement_centres.id',ondelete='CASCADE'),nullable=False); __table_args__=(db.UniqueConstraint('operator_id','centre_id',name='uq_operator_centre'),)
