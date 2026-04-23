import os
import re
import uuid6
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional, List
from models import Profile, Base 
from db_setup import SessionLocal, engine
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv


# 1. Setup & Config
DOTENV_PATH = ".env.local" if os.path.exists(".env.local") else ".env"
load_dotenv(DOTENV_PATH)
DATABASE_URL = os.getenv("POSTGRES_URL", "").replace("postgres://", "postgresql://", 1)

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

app = FastAPI()

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )

# CORS - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Database Model - Stage 2 Requirements
# class Profile(Base):
#     __tablename__ = "profiles"
#     id = Column(String, primary_key=True, index=True)
#     name = Column(String, unique=True, index=True, nullable=False)
#     gender = Column(String)
#     gender_probability = Column(Float)
#     age = Column(Integer)
#     age_group = Column(String)
#     country_id = Column(String, index=True)
#     country_name = Column(String)
#     country_probability = Column(Float)
#     created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Helper Functions
def calculate_age_group(age: int) -> str:
    """Calculate age group from age"""
    if 0 <= age <= 12:
        return "child"
    if 13 <= age <= 19:
        return "teenager"
    if 20 <= age <= 59:
        return "adult"
    return "senior"

async def fetch_external_data(name: str):
    """Fetch gender, age, and country data from external APIs"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        g_task = client.get(f"https://api.genderize.io?name={name}")
        a_task = client.get(f"https://api.agify.io?name={name}")
        n_task = client.get(f"https://api.nationalize.io?name={name}")
        
        res_g, res_a, res_n = await asyncio.gather(g_task, a_task, n_task)
        
        d_g = res_g.json()
        if not d_g.get("gender") or d_g.get("count", 0) == 0:
            raise HTTPException(status_code=502, detail="Genderize returned an invalid response")
            
        d_a = res_a.json()
        if d_a.get("age") is None:
            raise HTTPException(status_code=502, detail="Agify returned an invalid response")
            
        d_n = res_n.json()
        if not d_n.get("country"):
            raise HTTPException(status_code=502, detail="Nationalize returned an invalid response")
            
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

# Country code mapping for NLP
COUNTRY_CODE_MAP = {
    "nigeria": "NG", "nigerian": "NG",
    "kenya": "KE", "kenyan": "KE",
    "ghana": "GH", "ghanaian": "GH",
    "benin": "BJ", "beninese": "BJ",
    "south africa": "ZA", "south african": "ZA",
    "uganda": "UG", "ugandan": "UG",
    "cameroon": "CM", "cameroonian": "CM",
    "mozambique": "MZ", "mozambican": "MZ",
    "senegal": "SN", "senegalese": "SN",
    "tanzania": "TZ", "tanzanian": "TZ",
    "rwanda": "RW", "rwandan": "RW",
    "malawi": "MW", "malawian": "MW",
    "zambia": "ZM", "zambian": "ZM",
    "zimbabwe": "ZW", "zimbabwean": "ZW",
    "botswana": "BW", "batswana": "BW",
    "lesotho": "LS", "basotho": "LS",
    "eswatini": "SZ", "swazi": "SZ",
    "gabon": "GA", "gabonese": "GA",
    "congo": "CG", "congolese": "CG",
    "drc": "CD", "democratic republic": "CD",
    "liberia": "LR", "liberian": "LR",
    "sierra leone": "SL", "sierra leonean": "SL",
    "mauritius": "MU", "mauritian": "MU",
    "seychelles": "SC", "seychellois": "SC",
    "mauritania": "MR", "mauritanian": "MR",
    "sudan": "SD", "sudanese": "SD",
    "egypt": "EG", "egyptian": "EG",
    "morocco": "MA", "moroccan": "MA",
    "algeria": "DZ", "algerian": "DZ",
    "tunisia": "TN", "tunisian": "TN",
    "libiya": "LY", "libyan": "LY",
    "ethiopia": "ET", "ethiopian": "ET",
    "somalia": "SO", "somali": "SO",
    "angola": "AO", "angolan": "AO",
}

def parse_natural_language_query(query: str) -> dict:
    """Parse natural language query into filters"""
    query_lower = query.lower().strip()
    filters = {}
    
    # Gender detection
    if "male" in query_lower:
        filters["gender"] = "male"
    elif "female" in query_lower:
        filters["gender"] = "female"
    
    # Age group detection
    if "child" in query_lower or "children" in query_lower:
        filters["age_group"] = "child"
    elif "teenager" in query_lower or "teen" in query_lower:
        filters["age_group"] = "teenager"
        if "above 17" in query_lower or "above17" in query_lower or "> 17" in query_lower:
            filters["min_age"] = 17
    elif "adult" in query_lower:
        filters["age_group"] = "adult"
    elif "senior" in query_lower or "elderly" in query_lower:
        filters["age_group"] = "senior"
    
    # Young/old age mapping
    if "young" in query_lower and "age_group" not in filters:
        filters["min_age"] = 16
        filters["max_age"] = 24
    if "old" in query_lower or "senior" in query_lower:
        filters["min_age"] = 60
    
    # Country detection
    for country_name, country_code in COUNTRY_CODE_MAP.items():
        if country_name in query_lower:
            filters["country_id"] = country_code
            break
    
    # Age range detection using regex
    age_match = re.search(r'(\d+)\s*-\s*(\d+)', query_lower)
    if age_match:
        filters["min_age"] = int(age_match.group(1))
        filters["max_age"] = int(age_match.group(2))
    
    # Min age detection
    min_age_match = re.search(r'above\s+(\d+)|over\s+(\d+)|>\s*(\d+)|minimum\s+(\d+)', query_lower)
    if min_age_match:
        age_val = min_age_match.group(1) or min_age_match.group(2) or min_age_match.group(3) or min_age_match.group(4)
        filters["min_age"] = int(age_val)
    
    # Max age detection
    max_age_match = re.search(r'below\s+(\d+)|under\s+(\d+)|<\s*(\d+)|maximum\s+(\d+)', query_lower)
    if max_age_match:
        age_val = max_age_match.group(1) or max_age_match.group(2) or max_age_match.group(3) or max_age_match.group(4)
        filters["max_age"] = int(age_val)
    
    return filters

# 4. Endpoints

# Create database tables
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.post("/profiles", status_code=201)
async def create_profile(request: Request, db: Session = Depends(get_db)):
    """Create a new profile (Stage 1)"""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    name = payload.get("name")
    
    if not name or not isinstance(name, str) or name.strip() == "":
        raise HTTPException(status_code=400, detail="Missing or empty name")
    
    name = name.strip().lower()

    existing = db.query(Profile).filter(Profile.name == name).first()
    if existing:
        return {"status": "success", "message": "Profile already exists", "data": existing}
    
    ext_data = await fetch_external_data(name)
    
    new_profile = Profile(
        id=str(uuid6.uuid7()),
        name=name,
        **ext_data
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    
    return {"status": "success", "data": new_profile}

@app.get("/profiles")
def get_all_profiles(
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    min_gender_probability: Optional[float] = Query(None),
    min_country_probability: Optional[float] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get all profiles with filtering, sorting, and pagination (Stage 2)"""
    
    # Validate sort_by
    valid_sort_fields = ["age", "created_at", "gender_probability"]
    if sort_by and sort_by not in valid_sort_fields:
        raise HTTPException(status_code=422, detail=f"Invalid sort_by. Must be one of: {', '.join(valid_sort_fields)}")
    
    # Validate order
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=422, detail="Invalid order. Must be 'asc' or 'desc'")
    
    # Build query
    query = db.query(Profile)
    
    # Apply filters
    if gender:
        query = query.filter(Profile.gender == gender.lower())
    if age_group:
        query = query.filter(Profile.age_group == age_group.lower())
    if country_id:
        query = query.filter(Profile.country_id == country_id.upper())
    if min_age is not None:
        query = query.filter(Profile.age >= min_age)
    if max_age is not None:
        query = query.filter(Profile.age <= max_age)
    if min_gender_probability is not None:
        query = query.filter(Profile.gender_probability >= min_gender_probability)
    if min_country_probability is not None:
        query = query.filter(Profile.country_probability >= min_country_probability)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if sort_by == "age":
        sort_col = Profile.age
    elif sort_by == "created_at":
        sort_col = Profile.created_at
    elif sort_by == "gender_probability":
        sort_col = Profile.gender_probability
    else:
        sort_col = Profile.created_at  # Default sort
    
    if order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())
    
    # Apply pagination
    skip = (page - 1) * limit
    profiles = query.offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": profiles
    }

@app.get("/profiles/search")
def search_profiles(
    q: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Natural language search for profiles (Stage 2)"""
    
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Missing or empty query")
    
    # Parse natural language query
    filters = parse_natural_language_query(q)
    
    # If no filters could be extracted, return error
    if not filters:
        return {"status": "error", "message": "Unable to interpret query"}
    
    # Build query
    query = db.query(Profile)
    
    # Apply filters
    if "gender" in filters:
        query = query.filter(Profile.gender == filters["gender"])
    if "age_group" in filters:
        query = query.filter(Profile.age_group == filters["age_group"])
    if "country_id" in filters:
        query = query.filter(Profile.country_id == filters["country_id"])
    if "min_age" in filters:
        query = query.filter(Profile.age >= filters["min_age"])
    if "max_age" in filters:
        query = query.filter(Profile.age <= filters["max_age"])
    if "min_gender_probability" in filters:
        query = query.filter(Profile.gender_probability >= filters["min_gender_probability"])
    if "min_country_probability" in filters:
        query = query.filter(Profile.country_probability >= filters["min_country_probability"])
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    skip = (page - 1) * limit
    profiles = query.offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": profiles
    }

@app.get("/profiles/{profile_id}")
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    """Get a specific profile by ID"""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "success", "data": profile}

@app.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    """Delete a profile by ID"""
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()
    return None

@app.get("/health")
def health():
    return {"status": "ok", "message": "Server is running, database connection pending"}