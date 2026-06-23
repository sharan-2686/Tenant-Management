from fastapi import FastAPI,Depends,UploadFile,File
from pydantic import BaseModel
from db import engine,SessionLocal
from sqlalchemy.orm import Session
from dbmodels import Tenant as dbtenant
from pydantic import BaseModel
from typing import Optional
from pydantic import BaseModel
from typing import Optional
from db import supabase

app=FastAPI()

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
         