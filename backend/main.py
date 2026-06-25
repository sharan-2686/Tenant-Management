from fastapi import FastAPI,Depends,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from db import engine,SessionLocal
from sqlalchemy.orm import Session
from dbmodels import Tenant as dbtenant
from dbmodels import TenantStay, Room as dbroom, RentPayment as dbrentpayment, Property as dbproperty, User as dbuser, Bed as dbbed
import asyncio
import os
import razorpay
from typing import Optional, List
from db import supabase
from datetime import datetime, date, timedelta
from fastapi.exceptions import HTTPException
from dbmodels import Visitor as dbvisitor
from dbmodels import Feedback

app=FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TenantCreate(BaseModel):
 full_name: str
 email: Optional[str] = None
 phone: Optional[str] = None
 gender: Optional[str] = None


 aadhaar_number: Optional[str] = None
 pan_number: Optional[str] = None

 address: Optional[str] = None

 emergency_contact_name: Optional[str] = None
 emergency_contact_phone: Optional[str] = None

class TenantUpdate(BaseModel):
 full_name: Optional[str] = None
 email: Optional[str] = None
 phone: Optional[str] = None
 gender: Optional[str] = None
 aadhaar_number: Optional[str] = None
 pan_number: Optional[str] = None

 address: Optional[str] = None

 emergency_contact_name: Optional[str] = None
 emergency_contact_phone: Optional[str] = None


class KYCVerify(BaseModel):
 status: str
class VisitorCreate(BaseModel):
    tenant_id: int
    visitor_name: str
    visitor_phone: Optional[str] = None
    address: Optional[str] = None
    purpose: Optional[str] = None
class FeedbackCreate(BaseModel):
    tenant_id: int
    title: str
    description: str


class RentPayRequest(BaseModel):
    payment_method: str
    transaction_reference: Optional[str] = None
    paid_date: Optional[date] = None


class RentGenerationRequest(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None


class PropertyLinkRazorpayRequest(BaseModel):
    razorpay_account_id: str


class RentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class FeedbackResponse(BaseModel):
    id: int
    tenant_id: int
    title: str
    description: str
    status: str
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True

class UserRegister(BaseModel):
    full_name: str
    email: str
    phone: str
    password: str
    role: str # tenant, landlord, admin

class UserLogin(BaseModel):
    email: str
    password: str

def getdb():
   db=SessionLocal()
   try:
      yield db
   finally:
     db.close()
@app.post("/add-tenant")
def add_tenant(ten:TenantCreate,db:Session =Depends(getdb)):
      data=ten.model_dump()
      data.pop("status", None)
      new_tenant = dbtenant(**data)
  
      db.add(new_tenant)
      db.commit()
      db.refresh(new_tenant)
      return new_tenant
@app.put("/update-tenant/{id}")
def update_tenant(id: int, ten: TenantUpdate, db: Session = Depends(getdb)):

    target_tenant = db.query(dbtenant).filter(dbtenant.id == id).first()

    if not target_tenant:
        return {"error": "Tenant not found"}

    data = ten.model_dump(exclude_unset=True)

    target_tenant.full_name = data.get("full_name", target_tenant.full_name)
    target_tenant.email = data.get("email", target_tenant.email)
    target_tenant.phone = data.get("phone", target_tenant.phone)
    target_tenant.gender = data.get("gender", target_tenant.gender)

    target_tenant.aadhaar_number = data.get("aadhaar_number", target_tenant.aadhaar_number)
    target_tenant.pan_number = data.get("pan_number", target_tenant.pan_number)

    target_tenant.address = data.get("address", target_tenant.address)

    target_tenant.emergency_contact_name = data.get("emergency_contact_name", target_tenant.emergency_contact_name)
    target_tenant.emergency_contact_phone = data.get("emergency_contact_phone", target_tenant.emergency_contact_phone)

    db.commit()
    db.refresh(target_tenant)

    return target_tenant
@app.post("/upload-kyc/{tenant_id}")
def upload_kyc(
    tenant_id: int,
    aadhaar_pdf: UploadFile = File(...),
    pan_pdf: UploadFile = File(...),
    id_card_pdf: UploadFile = File(...),
    db: Session = Depends(getdb)
):

    tenant = db.query(dbtenant).filter(dbtenant.id == tenant_id).first()

    if not tenant:
        return {"error": "Tenant not found"}

    # ---------- Aadhaar Upload ----------
    aadhaar_name = f"aadhaar_{tenant_id}_{aadhaar_pdf.filename}"
    supabase.storage.from_("kyc-documents").upload(
        aadhaar_name,
        aadhaar_pdf.file.read(),
        {"content-type": "application/pdf"}
    )
    aadhaar_url = supabase.storage.from_("kyc-documents").get_public_url(aadhaar_name)

    # ---------- PAN Upload ----------
    pan_name = f"pan_{tenant_id}_{pan_pdf.filename}"
    supabase.storage.from_("kyc-documents").upload(
        pan_name,
        pan_pdf.file.read(),
        {"content-type": "application/pdf"}
    )
    pan_url = supabase.storage.from_("kyc-documents").get_public_url(pan_name)

    # ---------- ID Card Upload ----------
    id_name = f"id_{tenant_id}_{id_card_pdf.filename}"
    supabase.storage.from_("kyc-documents").upload(
        id_name,
        id_card_pdf.file.read(),
        {"content-type": "application/pdf"}
    )
    id_url = supabase.storage.from_("kyc-documents").get_public_url(id_name)

    # ---------- Save URLs in DB ----------
    tenant.aadhaar_pdf_url = aadhaar_url
    tenant.pan_pdf_url = pan_url
    tenant.id_card_pdf_url = id_url

    tenant.status = "under_review"
    db.commit()
    db.refresh(tenant)

    return {
        "message": "KYC uploaded successfully",
        "aadhaar": aadhaar_url,
        "pan": pan_url,
        "id_card": id_url
    }
@app.post("/checkin/{tenant_id}")
def checkin_tenant(
    tenant_id: int,
    db: Session = Depends(getdb)
):
    tenant = db.query(dbtenant).filter(
        dbtenant.id == tenant_id
    ).first()

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Tenant not found"
        )

    stay = TenantStay(
        tenant_id=tenant.id,
        property_id=tenant.property_id,
        room_id=tenant.room_id,
        bed_id=tenant.bed_id,
        stay_status="checked_in"
    )

    db.add(stay)

    
    db.commit()

    return {
        "message": "Tenant checked in successfully"
    }
@app.put("/checkout/{tenant_id}")
def checkout_tenant( tenant_id: int, db: Session = Depends(getdb)):
    stay = db.query(TenantStay).filter(
    TenantStay.tenant_id == tenant_id,
     TenantStay.stay_status == "checked_in"
    ).first()

    if not stay:
        raise HTTPException(
            status_code=404,
            detail="No active stay found"
        )

    stay.checkout_time = datetime.utcnow()
    stay.stay_status = "checked_out"

    tenant = db.query(dbtenant).filter(
        dbtenant.id == tenant_id
    ).first()

    

    db.commit()

    return {
        "message": "Tenant checked out successfully"
    }
@app.post("/add-visitor")
def add_visitor(vis: VisitorCreate, db: Session = Depends(getdb)):
   data = vis.model_dump()
   new_visitor = dbvisitor(**data)
   db.add(new_visitor)
   db.commit()
   db.refresh(new_visitor)
   return new_visitor

@app.post("/add-feedback")
def add_feedback(feedback: FeedbackCreate, db: Session = Depends(getdb)):

    new_feedback = Feedback(
        tenant_id=feedback.tenant_id,
        title=feedback.title,
        description=feedback.description
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    return new_feedback


@app.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
def track_status(feedback_id: int, db: Session = Depends(getdb)):

    complaint = db.query(Feedback).filter(
        Feedback.id == feedback_id
    ).first()

    return complaint


# --- Rent Payments Business Logic & Endpoints ---

def calculate_current_late_fee(due_date: date, paid_date: Optional[date] = None, payment_status: str = "pending", saved_late_fee: float = 0.0) -> float:
    if payment_status == "paid":
        return float(saved_late_fee)
    
    current_date = paid_date or date.today()
    if current_date <= due_date:
        return 0.0
    
    days_late = (current_date - due_date).days
    if days_late <= 3:  # 3 days grace period
        return 0.0
    
    return float(days_late * 100.0)  # Rs. 100 per day past due date


def generate_rent_bills_for_period(db: Session, year: int, month: int) -> dict:
    billing_period = f"{year}-{month:02d}"
    
    # Query all active stays to get currently checked-in tenant IDs
    active_stays = db.query(TenantStay).filter(TenantStay.stay_status == "checked_in").all()
    active_stay_tenant_ids = {stay.tenant_id for stay in active_stays}
    
    # Query tenants who are status="active" or have an active stay
    active_tenants = db.query(dbtenant).filter(
        (dbtenant.status == "active") | (dbtenant.id.in_(list(active_stay_tenant_ids)))
    ).filter(dbtenant.room_id.isnot(None)).all()
    
    generated_count = 0
    skipped_count = 0
    errors = []
    
    for tenant in active_tenants:
        # Check if rent bill already generated for this period
        existing_payment = db.query(dbrentpayment).filter(
            dbrentpayment.tenant_id == tenant.id,
            dbrentpayment.billing_period == billing_period
        ).first()
        
        if existing_payment:
            skipped_count += 1
            continue
            
        # Fetch the room rent amount
        room = db.query(dbroom).filter(dbroom.id == tenant.room_id).first()
        if not room:
            errors.append(f"Room ID {tenant.room_id} not found for tenant {tenant.full_name} (ID: {tenant.id})")
            continue
            
        # Rent is generated for this billing period; due date is set to the 5th of that month
        due_date = date(year, month, 5)
        
        new_payment = dbrentpayment(
            tenant_id=tenant.id,
            amount=room.monthly_rent,
            due_date=due_date,
            payment_status="pending",
            billing_period=billing_period,
            late_fee=0
        )
        db.add(new_payment)
        generated_count += 1
        
    db.commit()
    return {
        "billing_period": billing_period,
        "generated": generated_count,
        "skipped": skipped_count,
        "errors": errors
    }


def make_rent_payment_response(payment: dbrentpayment, db: Session, current_date: date = None) -> dict:
    if not current_date:
        current_date = date.today()
        
    late_fee = calculate_current_late_fee(
        due_date=payment.due_date,
        paid_date=payment.paid_date or current_date,
        payment_status=payment.payment_status,
        saved_late_fee=payment.late_fee or 0.0
    )
    
    tenant = db.query(dbtenant).filter(dbtenant.id == payment.tenant_id).first()
    tenant_name = tenant.full_name if tenant else None
    room_number = None
    if tenant and tenant.room_id:
        room = db.query(dbroom).filter(dbroom.id == tenant.room_id).first()
        if room:
            room_number = room.room_number
            
    return {
        "id": payment.id,
        "tenant_id": payment.tenant_id,
        "amount": float(payment.amount),
        "due_date": payment.due_date,
        "paid_date": payment.paid_date,
        "payment_method": payment.payment_method,
        "payment_status": payment.payment_status,
        "receipt_number": payment.receipt_number,
        "billing_period": payment.billing_period,
        "late_fee": late_fee,
        "total_amount": float(payment.amount) + late_fee,
        "created_at": payment.created_at,
        "tenant_name": tenant_name,
        "room_number": room_number,
        "razorpay_order_id": payment.razorpay_order_id,
        "razorpay_payment_id": payment.razorpay_payment_id
    }


async def auto_rent_generator_task():
    while True:
        try:
            await asyncio.sleep(3600)  # Check every 1 hour (runs initial check after startup)
            db = SessionLocal()
            try:
                now = datetime.now()
                # Run generator for current month/year
                result = generate_rent_bills_for_period(db, now.year, now.month)
                if result["generated"] > 0:
                    print(f"Auto rent generation: Generated {result['generated']} bills for period {result['billing_period']}")
            except Exception as e:
                print(f"Error in auto rent generator run: {e}")
            finally:
                db.close()
        except Exception as e:
            print(f"Error in background task loop: {e}")
        
        # Sleep for 12 hours before checking again
        await asyncio.sleep(43200)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_rent_generator_task())


@app.post("/rent/generate")
def trigger_rent_generation(req: Optional[RentGenerationRequest] = None, db: Session = Depends(getdb)):
    req_year = req.year if req and req.year else datetime.now().year
    req_month = req.month if req and req.month else datetime.now().month
    
    result = generate_rent_bills_for_period(db, req_year, req_month)
    return result


@app.get("/rent/dues")
def get_rent_dues(tenant_id: Optional[int] = None, db: Session = Depends(getdb)):
    query = db.query(dbrentpayment).filter(dbrentpayment.payment_status == "pending")
    if tenant_id:
        query = query.filter(dbrentpayment.tenant_id == tenant_id)
    payments = query.all()
    
    return [make_rent_payment_response(p, db) for p in payments]


@app.get("/rent/overdue")
def get_overdue_rents(db: Session = Depends(getdb)):
    today = date.today()
    payments = db.query(dbrentpayment).filter(
        dbrentpayment.payment_status == "pending",
        dbrentpayment.due_date < today
    ).all()
    
    return [make_rent_payment_response(p, db, today) for p in payments]


@app.get("/rent/tenant/{tenant_id}")
def get_tenant_rent_history(tenant_id: int, db: Session = Depends(getdb)):
    payments = db.query(dbrentpayment).filter(
        dbrentpayment.tenant_id == tenant_id
    ).order_by(dbrentpayment.due_date.desc()).all()
    
    return [make_rent_payment_response(p, db) for p in payments]


@app.post("/rent/pay/{payment_id}")
def pay_rent(payment_id: int, req: RentPayRequest, db: Session = Depends(getdb)):
    payment = db.query(dbrentpayment).filter(dbrentpayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Rent payment not found")
        
    if payment.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Rent payment is already paid")
        
    paid_date = req.paid_date or date.today()
    
    # Calculate late fee at the time of payment
    late_fee = calculate_current_late_fee(
        due_date=payment.due_date,
        paid_date=paid_date,
        payment_status="pending",
        saved_late_fee=0.0
    )
    
    payment.payment_status = "paid"
    payment.paid_date = paid_date
    payment.payment_method = req.payment_method
    payment.late_fee = late_fee
    payment.receipt_number = req.transaction_reference or f"REC-{payment.id}-{int(datetime.utcnow().timestamp())}"
    
    db.commit()
    db.refresh(payment)
    
    return make_rent_payment_response(payment, db, paid_date)


# --- Razorpay Route Integration Client & Endpoints ---

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_dummy_key_id")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "dummy_key_secret")

try:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
except Exception as e:
    print(f"Error initializing Razorpay Client: {e}")
    razorpay_client = None


@app.post("/properties/{property_id}/link-razorpay")
def link_property_razorpay(property_id: int, req: PropertyLinkRazorpayRequest, db: Session = Depends(getdb)):
    property_obj = db.query(dbproperty).filter(dbproperty.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
        
    property_obj.razorpay_account_id = req.razorpay_account_id
    db.commit()
    db.refresh(property_obj)
    
    return {
        "message": "Property linked to Razorpay successfully",
        "property_id": property_id,
        "razorpay_account_id": property_obj.razorpay_account_id
    }


@app.post("/rent/checkout/{payment_id}")
def create_checkout_session(payment_id: int, db: Session = Depends(getdb)):
    # 1. Fetch rent details
    payment = db.query(dbrentpayment).filter(dbrentpayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Rent payment not found")
        
    if payment.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Rent payment is already paid")
        
    # Calculate total amount (base + late fee)
    late_fee = calculate_current_late_fee(
        due_date=payment.due_date,
        paid_date=None,
        payment_status="pending",
        saved_late_fee=0.0
    )
    total_amount = float(payment.amount) + late_fee
    total_amount_in_paise = int(total_amount * 100) # Razorpay works in paise

    # 2. Get property and check for linked Razorpay Account ID
    tenant = db.query(dbtenant).filter(dbtenant.id == payment.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    property_obj = db.query(dbproperty).filter(dbproperty.id == tenant.property_id).first()
    if not property_obj or not property_obj.razorpay_account_id:
        raise HTTPException(
            status_code=400, 
            detail=f"Property has no linked Razorpay Account ID."
        )

    # 3. Create the Razorpay Order with split transfers (Razorpay Route)
    # Platform commission is 2% of total_amount, remainder goes to property owner
    commission_rate = 0.02
    platform_fee = total_amount * commission_rate
    landlord_amount = total_amount - platform_fee
    landlord_amount_in_paise = int(landlord_amount * 100)

    order_payload = {
        "amount": total_amount_in_paise,
        "currency": "INR",
        "receipt": f"receipt_{payment.id}_{int(datetime.utcnow().timestamp())}",
        "transfers": [
            {
                "account": property_obj.razorpay_account_id,
                "amount": landlord_amount_in_paise,
                "currency": "INR",
                "notes": {
                    "payment_id": str(payment.id),
                    "type": "rent_split"
                },
                "linked_account_notes": [
                    "payment_id"
                ],
                "on_hold": False
            }
        ]
    }

    try:
        # Create order in Razorpay
        order = razorpay_client.order.create(data=order_payload)
        
        # Save order ID in db
        payment.razorpay_order_id = order["id"]
        db.commit()
        db.refresh(payment)
        
        return {
            "order_id": order["id"],
            "amount": total_amount,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID,
            "landlord_amount": landlord_amount,
            "platform_fee": platform_fee
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay Order: {str(e)}")


@app.post("/rent/verify")
def verify_razorpay_payment(req: RentVerifyRequest, db: Session = Depends(getdb)):
    # 1. Fetch the payment record
    payment = db.query(dbrentpayment).filter(dbrentpayment.razorpay_order_id == req.razorpay_order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Rent payment order not found")
        
    if payment.payment_status == "paid":
        return make_rent_payment_response(payment, db)

    # 2. Verify signature
    params_dict = {
        'razorpay_order_id': req.razorpay_order_id,
        'razorpay_payment_id': req.razorpay_payment_id,
        'razorpay_signature': req.razorpay_signature
    }

    try:
        # Verify signature
        razorpay_client.utility.verify_payment_signature(params_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment signature verification failed: {str(e)}")

    # 3. Mark rent payment as paid
    paid_date = date.today()
    
    # Calculate late fee at time of verification
    late_fee = calculate_current_late_fee(
        due_date=payment.due_date,
        paid_date=paid_date,
        payment_status="pending",
        saved_late_fee=0.0
    )

    payment.payment_status = "paid"
    payment.paid_date = paid_date
    payment.payment_method = "Razorpay"
    payment.late_fee = late_fee
    payment.razorpay_payment_id = req.razorpay_payment_id
    payment.receipt_number = f"REC-RZP-{req.razorpay_payment_id}"
    
    db.commit()
    db.refresh(payment)

    return make_rent_payment_response(payment, db, paid_date)


# --- Additional Mobile App API Endpoints ---

@app.post("/register")
def register_user(user: UserRegister, db: Session = Depends(getdb)):
    existing = db.query(dbuser).filter((dbuser.email == user.email) | (dbuser.phone == user.phone)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email or phone already registered")
    new_user = dbuser(
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        password_hash=user.password,  # Storing as is for development/mocking
        role=user.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "id": new_user.id, "role": new_user.role}


@app.post("/login")
def login_user(user: UserLogin, db: Session = Depends(getdb)):
    db_user = db.query(dbuser).filter(dbuser.email == user.email).first()
    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is also a tenant to return tenant_id
    tenant_id = None
    if db_user.role == "tenant":
        tenant = db.query(dbtenant).filter(dbtenant.email == db_user.email).first()
        if tenant:
            tenant_id = tenant.id
    
    return {
        "message": "Login successful",
        "user_id": db_user.id,
        "full_name": db_user.full_name,
        "email": db_user.email,
        "phone": db_user.phone,
        "role": db_user.role,
        "tenant_id": tenant_id
    }


@app.get("/properties")
def get_properties(db: Session = Depends(getdb)):
    return db.query(dbproperty).all()


@app.get("/properties/{property_id}/rooms")
def get_property_rooms(property_id: int, db: Session = Depends(getdb)):
    return db.query(dbroom).filter(dbroom.property_id == property_id).all()


@app.get("/rooms/{room_id}/beds")
def get_room_beds(room_id: int, db: Session = Depends(getdb)):
    return db.query(dbbed).filter(dbbed.room_id == room_id).all()


@app.get("/tenants")
def get_tenants(property_id: Optional[int] = None, db: Session = Depends(getdb)):
    query = db.query(dbtenant)
    if property_id:
        query = query.filter(dbtenant.property_id == property_id)
    return query.all()


@app.get("/tenants/{tenant_id}")
def get_tenant_details(tenant_id: int, db: Session = Depends(getdb)):
    tenant = db.query(dbtenant).filter(dbtenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Fetch active stay info if any
    stay = db.query(TenantStay).filter(
        TenantStay.tenant_id == tenant_id,
        TenantStay.stay_status == "checked_in"
    ).first()
    
    # Get room and bed info
    room_number = None
    property_name = None
    bed_number = None
    if tenant.room_id:
        room = db.query(dbroom).filter(dbroom.id == tenant.room_id).first()
        if room:
            room_number = room.room_number
    if tenant.property_id:
        prop = db.query(dbproperty).filter(dbproperty.id == tenant.property_id).first()
        if prop:
            property_name = prop.property_name
    if tenant.bed_id:
        bed = db.query(dbbed).filter(dbbed.id == tenant.bed_id).first()
        if bed:
            bed_number = bed.bed_number

    return {
        "id": tenant.id,
        "full_name": tenant.full_name,
        "email": tenant.email,
        "phone": tenant.phone,
        "gender": tenant.gender,
        "status": tenant.status,
        "property_id": tenant.property_id,
        "property_name": property_name,
        "room_id": tenant.room_id,
        "room_number": room_number,
        "bed_id": tenant.bed_id,
        "bed_number": bed_number,
        "checkin_date": tenant.checkin_date,
        "checkout_date": tenant.checkout_date,
        "security_deposit": float(tenant.security_deposit) if tenant.security_deposit else 0.0,
        "aadhaar_number": tenant.aadhaar_number,
        "pan_number": tenant.pan_number,
        "address": tenant.address,
        "emergency_contact_name": tenant.emergency_contact_name,
        "emergency_contact_phone": tenant.emergency_contact_phone,
        "aadhaar_pdf_url": tenant.aadhaar_pdf_url,
        "pan_pdf_url": tenant.pan_pdf_url,
        "id_card_pdf_url": tenant.id_card_pdf_url,
        "has_active_stay": stay is not None
    }


@app.get("/feedback")
def get_all_feedback(db: Session = Depends(getdb)):
    feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
    response_data = []
    for fb in feedbacks:
        tenant = db.query(dbtenant).filter(dbtenant.id == fb.tenant_id).first()
        tenant_name = tenant.full_name if tenant else f"Tenant #{fb.tenant_id}"
        response_data.append({
            "id": fb.id,
            "tenant_id": fb.tenant_id,
            "tenant_name": tenant_name,
            "title": fb.title,
            "description": fb.description,
            "status": fb.status,
            "created_at": fb.created_at,
            "resolved_at": fb.resolved_at
        })
    return response_data


@app.get("/feedback/tenant/{tenant_id}")
def get_tenant_feedback(tenant_id: int, db: Session = Depends(getdb)):
    return db.query(Feedback).filter(Feedback.tenant_id == tenant_id).order_by(Feedback.created_at.desc()).all()


@app.post("/feedback/{feedback_id}/resolve")
def resolve_feedback(feedback_id: int, db: Session = Depends(getdb)):
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    fb.status = "resolved"
    fb.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(fb)
    return fb


@app.get("/landlord/stats")
def get_landlord_stats(db: Session = Depends(getdb)):
    total_properties = db.query(dbproperty).count()
    total_beds = db.query(dbbed).count()
    occupied_beds = db.query(dbbed).filter(dbbed.status == "occupied").count()
    occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0.0
    
    pending_payments = db.query(dbrentpayment).filter(dbrentpayment.payment_status == "pending").all()
    total_pending_dues = sum(float(p.amount) for p in pending_payments)
    
    total_complaints = db.query(Feedback).count()
    pending_complaints = db.query(Feedback).filter(Feedback.status == "in_progress").count()
    
    return {
        "total_properties": total_properties,
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "occupancy_rate": round(occupancy_rate, 2),
        "total_pending_dues": total_pending_dues,
        "total_complaints": total_complaints,
        "pending_complaints": pending_complaints
    }