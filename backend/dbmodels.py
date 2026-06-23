from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text,ForeignKey
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