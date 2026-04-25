from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel, EmailStr
import secrets
import time

app = FastAPI(
    title="India Location API - SaaS Edition",
    description="Secure B2B API for Indian Geographical Data",
    version="1.2.0"
)

# --- 1. AGGRESSIVE CORS FIX ---
# This ensures Swagger UI and other websites can talk to your API without "Failed to fetch"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- 2. DATABASE SETUP ---
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI, pool_pre_ping=True)

# --- 3. STARTUP FIX (Bypasses Neon SQL Editor Glitches) ---
@app.on_event("startup")
def startup_event():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_users (
                user_id SERIAL PRIMARY KEY,
                organization_name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                api_key VARCHAR(100) UNIQUE,
                plan_type VARCHAR(50) DEFAULT 'free',
                request_limit INTEGER DEFAULT 1000,
                current_usage INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true
            );
            
            CREATE TABLE IF NOT EXISTS api_usage_logs (
                log_id SERIAL PRIMARY KEY,
                api_key VARCHAR(100),
                endpoint VARCHAR(100),
                response_time_ms FLOAT,
                status_code INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- This ensures you always have a working key for your demo
            INSERT INTO api_users (organization_name, email, api_key, request_limit)
            VALUES ('Intern Demo', 'demo@example.com', 'capstone_demo_2024', 5000)
            ON CONFLICT DO NOTHING;
        """))
        conn.commit()

# --- 4. MODELS ---
class UserRegistration(BaseModel):
    organization_name: str
    email: EmailStr
    plan_type: str = "free"

# --- 5. AUTHENTICATION ---
async def verify_api_key(api_key: str = Header(None, alias="api-key")):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing api-key in Header")
    
    with engine.connect() as conn:
        query = text("SELECT * FROM api_users WHERE api_key = :k AND is_active = true")
        user = conn.execute(query, {"k": api_key}).mappings().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        # Check quota
        if user['current_usage'] >= user['request_limit']:
            raise HTTPException(status_code=429, detail="API Limit reached")
            
        # Log usage count
        conn.execute(
            text("UPDATE api_users SET current_usage = current_usage + 1 WHERE api_key = :k"), 
            {"k": api_key}
        )
        conn.commit()
        return user

# --- 6. ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Online", "gateway": "SaaS v1.2", "docs": "/docs"}

@app.post("/register")
def register(user: UserRegistration):
    new_key = f"india_loc_{secrets.token_urlsafe(16)}"
    limit = 1000 if user.plan_type == "free" else 10000
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO api_users (organization_name, email, api_key, request_limit, plan_type) 
                VALUES (:o, :e, :k, :l, :p)
            """),
            {"o": user.organization_name, "e": user.email, "k": new_key, "l": limit, "p": user.plan_type}
        )
        conn.commit()
    return {"api_key": new_key, "message": "Save this key for API access!"}

@app.get("/search")
def search(q: str, user=Depends(verify_api_key)):
    start_time = time.time()
    with engine.connect() as conn:
        # Using standard ILIKE to bypass the pg_trgm extension requirement
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
    return {
        "results": [dict(r) for r in results],
        "meta": {"took_ms": round(duration, 2), "quota_used": f"{user['current_usage'] + 1}/{user['request_limit']}"}
    }

@app.get("/states")
def get_states(user=Depends(verify_api_key)):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM states ORDER BY state_name")).mappings().all()
    return {"states": [dict(r) for r in res]}
