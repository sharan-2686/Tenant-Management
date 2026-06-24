from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Date, Numeric, Boolean
from datetime import datetime

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)

    # basic details
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=True)
    phone = Column(String(15), nullable=True)
    gender = Column(String(20), nullable=True)

    # KYC details
    aadhaar_number = Column(String(20), nullable=True)
    pan_number = Column(String(20), nullable=True)

    # address info
    address = Column(Text, nullable=True)

    # emergency contact
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(15), nullable=True)

    # status tracking
    status = Column(String(30), default="pending_kyc")

    # timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    aadhaar_pdf_url = Column(String, nullable=True)
    pan_pdf_url = Column(String, nullable=True)
    id_card_pdf_url = Column(String, nullable=True)

    # Missing database columns
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    bed_id = Column(Integer, ForeignKey("beds.id"), nullable=True)
    checkin_date = Column(Date, nullable=True)
    checkout_date = Column(Date, nullable=True)
    security_deposit = Column(Numeric, nullable=True)

class TenantStay(Base):
    __tablename__ = "tenant_stays"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id")
    )

    property_id = Column(
        Integer
    )

    room_id = Column(
        Integer
    )

    checkin_time = Column(
        DateTime,
        default=datetime.utcnow
    )

    checkout_time = Column(
        DateTime,
        nullable=True
    )

    stay_status = Column(
        String,
        default="checked_in"
    )

    remarks = Column(Text)
class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(Integer, ForeignKey("tenants.id"))

    visitor_name = Column(String(100), nullable=False)
    visitor_phone = Column(String(15))
    address = Column(Text)
    purpose = Column(Text)

    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime)

    status = Column(String(20), default="inside")

class Feedback(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    status = Column(String(50), default="in_progress")

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    property_name = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    owner_name = Column(String, nullable=True)
    owner_phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    razorpay_account_id = Column(String, nullable=True)


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    room_number = Column(String, nullable=False)
    room_type = Column(String, nullable=True)
    capacity = Column(Integer, nullable=False)
    monthly_rent = Column(Numeric, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RentPayment(Base):
    __tablename__ = "rent_payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    amount = Column(Numeric, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    payment_method = Column(String, nullable=True)
    payment_status = Column(String, default="pending")
    receipt_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    billing_period = Column(String(10), nullable=True)
    late_fee = Column(Numeric, default=0)
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    bed_number = Column(String, nullable=False)
    status = Column(String, default="available")


