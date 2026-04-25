from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel, EmailStr
import secrets
import time
from typing import List, Optional

app = FastAPI(
    title="India Location API - SaaS Edition",
    description="Secure B2B API for Indian Geographical Data",
    version="1.2.0"
)

# Enable CORS for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE SETUP ---
# Standard Neon connection string without channel_binding for maximum stability
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI, pool_pre_ping=True)

# --- MODELS ---
class UserRegistration(BaseModel):
    organization_name: str
    email: EmailStr
    plan_type: str = "free"  # free, premium, or pro

class SearchResult(BaseModel):
    name: str
    district_name: str
    state_name: str
    type: str

# --- ANALYTICS LOGGING ---
def log_usage(api_key: str, endpoint: str, duration: float, status: int):
    """Saves API performance metrics to the database"""
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO api_usage_logs (api_key, endpoint, response_time_ms, status_code)
                    VALUES (:k, :e, :t, :s)
                """),
                {"k": api_key, "e": endpoint, "t": duration, "s": status}
            )
            conn.commit()
    except Exception as e:
        print(f"Logging error: {e}")

# --- SECURITY MIDDLEWARE ---
async def verify_api_key(api_key: str = Header(None, alias="api-key")):
    """Validates the B2B API Key and manages request quotas"""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing api-key in Header")
    
    with engine.connect() as conn:
        query = text("SELECT * FROM api_users WHERE api_key = :k AND is_active = true")
        user = conn.execute(query, {"k": api_key}).mappings().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        if user['current_usage'] >= user['request_limit']:
            raise HTTPException(status_code=429, detail="Monthly request quota reached")
            
        # Increment usage counter
        conn.execute(
            text("UPDATE api_users SET current_usage = current_usage + 1 WHERE api_key = :k"),
            {"k": api_key}
        )
        conn.commit()
        return user

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Online", "message": "India Location SaaS API v1.2", "docs": "/docs"}

@app.post("/register")
def register_organization(user: UserRegistration):
    """Endpoint for new B2B partners to get an API Key"""
    new_key = f"india_loc_{secrets.token_urlsafe(16)}"
    # Set limits based on internship plan logic
    limit = 1000 if user.plan_type == "free" else 10000
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO api_users (organization_name, email, api_key, request_limit, plan_type)
                    VALUES (:o, :e, :k, :l, :p)
                """),
                {"o": user.organization_name, "e": user.email, "k": new_key, "l": limit, "p": user.plan_type}
            )
            conn.commit()
        return {"api_key": new_key, "organization": user.organization_name, "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Registration failed (Email might already exist)")

@app.get("/search")
def search_locations(q: str, user=Depends(verify_api_key)):
    """Advanced fuzzy search across 580k+ records using SQL Trigram Indexes"""
    start_time = time.time()
    
    if len(q) < 3:
        raise HTTPException(status_code=400, detail="Search query must be at least 3 characters")
    
    with engine.connect() as conn:
        query = text("""
            SELECT v.village_name as name, d.district_name, s.state_name, 'village' as type
            FROM villages v
            JOIN districts d ON v.district_id = d.district_id
            JOIN states s ON d.state_id = s.state_id
            WHERE v.village_name ILIKE :q
            LIMIT 10
        """)
        results = conn.execute(query, {"q": f"%{q}%"}).mappings().all()
    
    duration = (time.time() - start_time) * 1000
    log_usage(user['api_key'], "/search", duration, 200)
    
    return {
        "results": [dict(r) for r in results],
        "meta": {
            "query": q,
            "latency_ms": round(duration, 2),
            "usage": f"{user['current_usage'] + 1}/{user['request_limit']}"
        }
    }

@app.get("/states")
def get_states(user=Depends(verify_api_key)):
    """Fetch all states from the master table"""
    start_time = time.time()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM states ORDER BY state_name")).mappings().all()
    
    duration = (time.time() - start_time) * 1000
    log_usage(user['api_key'], "/states", duration, 200)
    return {"states": [dict(r) for r in res]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
