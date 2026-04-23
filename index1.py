import os
import re
import uuid6
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# 1. DATABASE CONFIG & SETUP
load_dotenv(".env.local" if os.path.exists(".env.local") else ".env")

DATABASE_URL = os.getenv("POSTGRES_URL", os.getenv("DATABASE_URL", "sqlite:///./test.db"))
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. DATABASE MODEL
class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(String, primary_key=True, index=True) 
    name = Column(String, unique=True, index=True, nullable=False)
    gender = Column(String)
    gender_probability = Column(Float)
    age = Column(Integer)
    age_group = Column(String) 
    country_id = Column(String(2)) 
    country_name = Column(String)
    country_probability = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "gender_probability": self.gender_probability,
            "age": self.age,
            "age_group": self.age_group,
            "country_id": self.country_id,
            "country_name": self.country_name,
            "country_probability": self.country_probability,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# 3. FASTAPI APP INITIALIZATION
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

# 4. HELPER FUNCTIONS & MAPPINGS
COUNTRY_CODE_MAP = {
    "nigeria": "NG", "nigerian": "NG", "kenya": "KE", "kenyan": "KE",
    "ghana": "GH", "ghanaian": "GH", "benin": "BJ", "beninese": "BJ",
    "south africa": "ZA", "south african": "ZA", "uganda": "UG", "ugandan": "UG",
    "cameroon": "CM", "cameroonian": "CM", "mozambique": "MZ", "mozambican": "MZ",
    "senegal": "SN", "senegalese": "SN", "tanzania": "TZ", "tanzanian": "TZ",
    "rwanda": "RW", "rwandan": "RW", "malawi": "MW", "malawian": "MW",
    "zambia": "ZM", "zambian": "ZM", "zimbabwe": "ZW", "zimbabwean": "ZW",
    "botswana": "BW", "batswana": "BW", "lesotho": "LS", "basotho": "LS",
    "eswatini": "SZ", "swazi": "SZ", "gabon": "GA", "gabonese": "GA",
    "congo": "CG", "congolese": "CG", "drc": "CD", "democratic republic": "CD",
    "liberia": "LR", "liberian": "LR", "sierra leone": "SL", "sierra leonean": "SL",
    "mauritius": "MU", "mauritian": "MU", "seychelles": "SC", "seychellois": "SC",
    "mauritania": "MR", "mauritanian": "MR", "sudan": "SD", "sudanese": "SD",
    "egypt": "EG", "egyptian": "EG", "morocco": "MA", "moroccan": "MA",
    "algeria": "DZ", "algerian": "DZ", "tunisia": "TN", "tunisian": "TN",
    "libiya": "LY", "libyan": "LY", "ethiopia": "ET", "ethiopian": "ET",
    "somalia": "SO", "somali": "SO", "angola": "AO", "angolan": "AO",
}

def calculate_age_group(age: int) -> str:
    if 0 <= age <= 12: return "child"
    if 13 <= age <= 19: return "teenager"
    if 20 <= age <= 59: return "adult"
    return "senior"

async def fetch_external_data(name: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        g_task = client.get(f"https://api.genderize.io?name={name}")
        a_task = client.get(f"https://api.agify.io?name={name}")
        n_task = client.get(f"https://api.nationalize.io?name={name}")
        
        res_g, res_a, res_n = await asyncio.gather(g_task, a_task, n_task)
        
        d_g, d_a, d_n = res_g.json(), res_a.json(), res_n.json()
        
        if not d_g.get("gender") or d_a.get("age") is None or not d_n.get("country"):
            raise HTTPException(status_code=502, detail="External API error")
            
        top_country = max(d_n["country"], key=lambda x: x["probability"])
        
        return {
            "gender": d_g["gender"],
            "gender_probability": d_g["probability"],
            "age": d_a["age"],
            "age_group": calculate_age_group(d_a["age"]),
            "country_id": top_country["country_id"],
            "country_name": top_country["country"],
            "country_probability": top_country["probability"]
        }

def parse_natural_language_query(query: str) -> dict:
    query_lower = query.lower().strip()
    filters = {}
    if "male" in query_lower: filters["gender"] = "male"
    elif "female" in query_lower: filters["gender"] = "female"
    for country_name, country_code in COUNTRY_CODE_MAP.items():
        if country_name in query_lower:
            filters["country_id"] = country_code
            break
    return filters

# 5. API ENDPOINTS
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Server is running"}

@app.post("/api/profiles", status_code=201)
async def create_profile(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    name = payload.get("name", "").strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Missing name")

    existing = db.query(Profile).filter(Profile.name == name).first()
    if existing:
        return {"status": "success", "message": "Profile already exists", "data": existing}
    
    ext_data = await fetch_external_data(name)
    new_profile = Profile(id=str(uuid6.uuid7()), name=name, **ext_data)
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return {"status": "success", "data": new_profile}

@app.get("/api/profiles")
def get_all_profiles(
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    query = db.query(Profile)
    if gender: query = query.filter(Profile.gender == gender.lower())
    if age_group: query = query.filter(Profile.age_group == age_group.lower())
    if country_id: query = query.filter(Profile.country_id == country_id.upper())
    
    total = query.count()
    profiles = query.offset((page - 1) * limit).limit(limit).all()
    return {"status": "success", "page": page, "limit": limit, "total": total, "data": profiles}

@app.get("/api/profiles/search")
def search_profiles(q: str = Query(...), db: Session = Depends(get_db)):
    filters = parse_natural_language_query(q)
    if not filters:
        return {"status": "error", "message": "Unable to interpret query"}
    
    query = db.query(Profile)
    if "gender" in filters: query = query.filter(Profile.gender == filters["gender"])
    if "country_id" in filters: query = query.filter(Profile.country_id == filters["country_id"])
    
    return {"status": "success", "total": query.count(), "data": query.all()}

@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile: raise HTTPException(status_code=404, detail="Not found")
    return {"status": "success", "data": profile}

@app.delete("/api/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile: raise HTTPException(status_code=404, detail="Not found")
    db.delete(profile)
    db.commit()
    return None
