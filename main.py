import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Schemas (aligned with schemas.py) ====
class Brand(BaseModel):
    name: str
    phone: Optional[str] = None
    logo_url: Optional[str] = None

class ReceiptItem(BaseModel):
    name: str
    quantity: int = Field(1, ge=1)
    price: float = Field(..., ge=0)

class ReceiptCreate(BaseModel):
    customer_name: Optional[str] = None
    items: List[ReceiptItem] = Field(default_factory=list)
    notes: Optional[str] = None

class ReceiptOut(BaseModel):
    number: int
    brand: Brand
    customer_name: Optional[str] = None
    items: List[ReceiptItem]
    notes: Optional[str] = None
    subtotal: float
    total: float
    created_at: datetime
    updated_at: datetime

# ==== Helpers ====
BRAND = Brand(
    name="VELLIXAO",
    phone="085706400133",
    logo_url="https://files.catbox.moe/a9u0pd.png",
)

COUNTER_ID = "receipt_number"
RECEIPT_COLLECTION = "receipt"
COUNTERS_COLLECTION = "counters"


def _get_next_receipt_number() -> int:
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db[COUNTERS_COLLECTION].find_one_and_update(
        {"_id": COUNTER_ID},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    # When upserting, seq may not exist yet; set default 1
    if doc is None:
        # extremely unlikely, but ensure fallback
        db[COUNTERS_COLLECTION].insert_one({"_id": COUNTER_ID, "seq": 1})
        return 1
    if "seq" not in doc:
        # Initialize to 1 on first creation
        db[COUNTERS_COLLECTION].update_one({"_id": COUNTER_ID}, {"$set": {"seq": 1}})
        return 1
    return int(doc["seq"])


def _compute_totals(items: List[ReceiptItem]) -> float:
    return float(sum(i.quantity * i.price for i in items))


@app.get("/")
def read_root():
    return {"message": "Receipt API is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


@app.post("/api/receipts", response_model=ReceiptOut)
def create_receipt(payload: ReceiptCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    number = _get_next_receipt_number()
    now = datetime.now(timezone.utc)
    items = payload.items or []
    subtotal = _compute_totals(items)
    total = subtotal  # extend here if you need taxes/fees

    doc = {
        "number": number,
        "brand": BRAND.model_dump(),
        "customer_name": payload.customer_name,
        "items": [i.model_dump() for i in items],
        "notes": payload.notes,
        "subtotal": subtotal,
        "total": total,
        "created_at": now,
        "updated_at": now,
    }

    db[RECEIPT_COLLECTION].insert_one(doc)

    return ReceiptOut(**doc)


@app.get("/api/receipts/latest", response_model=ReceiptOut)
def get_latest_receipt():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db[RECEIPT_COLLECTION].find_one(sort=[("number", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No receipts found")
    # Convert ObjectId and ensure datetime types are returned
    doc.pop("_id", None)
    return ReceiptOut(**doc)


@app.get("/api/receipts/{number}", response_model=ReceiptOut)
def get_receipt_by_number(number: int):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db[RECEIPT_COLLECTION].find_one({"number": number})
    if not doc:
        raise HTTPException(status_code=404, detail="Receipt not found")
    doc.pop("_id", None)
    return ReceiptOut(**doc)


@app.get("/api/receipts", response_model=list[ReceiptOut])
def list_receipts(limit: int = 20):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    cursor = db[RECEIPT_COLLECTION].find().sort("number", -1).limit(limit)
    results = []
    for d in cursor:
        d.pop("_id", None)
        results.append(ReceiptOut(**d))
    return results


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
