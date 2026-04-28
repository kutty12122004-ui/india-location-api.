import os
import time
import secrets
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel, EmailStr

# --- 1. APP SETUP ---
app = FastAPI(
    title="India Location API - SaaS Edition",
    description="Secure B2B API for Indian Geographical Data",
    version="1.3.0"
)

# Aggressive CORS for frontend/Swagger compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- 2. DATABASE SETUP ---
# Update this if your Neon connection string ever changes
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI, pool_pre_ping=True)

# --- 3. STARTUP SCHEMA SYNC ---
@app.on_event("startup")
def startup_event():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_users (
                id SERIAL PRIMARY KEY,
                organization_name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                api_key VARCHAR(100) UNIQUE NOT NULL,
                plan_type VARCHAR(50) DEFAULT 'free',
                request_limit INTEGER DEFAULT 1000,
                current_usage INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true
            );
            
            -- Ensure the demo key always exists
            INSERT INTO api_users (organization_name, email, api_key, request_limit)
            VALUES ('Demo User', 'demo@test.com', 'capstone_demo_2024', 5000)
            ON CONFLICT (api_key) DO NOTHING;
        """))
        conn.commit()

# --- 4. MODELS ---
class UserRegistration(BaseModel):
    organization_name: str
    email: EmailStr
    plan_type: str = "free"

# --- 5. AUTHENTICATION LOGIC ---
async def verify_api_key(api_key: str = Header(None, alias="api-key")):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing api-key in Header")
    
    with engine.connect() as conn:
        query = text("SELECT * FROM api_users WHERE api_key = :k AND is_active = true")
        user = conn.execute(query, {"k": api_key}).mappings().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        if user['current_usage'] >= user['request_limit']:
            raise HTTPException(status_code=429, detail="API Limit reached")
        
        # Increment usage count in database
        conn.execute(
            text("UPDATE api_users SET current_usage = current_usage + 1 WHERE api_key = :k"),
            {"k": api_key}
        )
        conn.commit()
        return user

# --- 6. ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "Online", "gateway": "SaaS v1.3", "docs": "/docs"}

@app.post("/register")
def register(user: UserRegistration):
    new_key = f"india_loc_{secrets.token_urlsafe(16)}"
    limit = 2000 if user.plan_type != "free" else 1000
    with engine.connect() as conn:
        try:
            conn.execute(
                text("""
                    INSERT INTO api_users (organization_name, email, api_key, request_limit, plan_type)
                    VALUES (:o, :e, :k, :l, :p)
                """),
                {"o": user.organization_name, "e": user.email, "k": new_key, "l": limit, "p": user.plan_type}
            )
            conn.commit()
            return {"api_key": new_key, "message": "Registration successful! Save your key."}
        except Exception as e:
            raise HTTPException(status_code=400, detail="Email already registered")

@app.get("/states")
def get_states(user=Depends(verify_api_key)):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT state_id, state_name FROM states ORDER BY state_name")).mappings().all()
    return {"total_states": len(res), "states": [dict(r) for r in res]}

@app.get("/districts/{state_id}")
def get_districts(state_id: int, user=Depends(verify_api_key)):
    with engine.connect() as conn:
        query = text("SELECT district_id, district_name FROM districts WHERE state_id = :s ORDER BY district_name")
        res = conn.execute(query, {"s": state_id}).mappings().all()
    return {"state_id": state_id, "districts": [dict(r) for r in res]}

@app.get("/search")
def search(q: str, state_id: int = None, user=Depends(verify_api_key)):
    start_time = time.time()
    with engine.connect() as conn:
        # Base query
        sql = """
            SELECT v.village_name as name, d.district_name, s.state_name, 'village' as type
            FROM villages v
            JOIN districts d ON v.district_id = d.district_id
            JOIN states s ON d.state_id = s.state_id
            WHERE v.village_name ILIKE :q
        """
        params = {"q": f"%{q}%"}
        
        # Optional State Filter
        if state_id:
            sql += " AND s.state_id = :sid"
            params["sid"] = state_id
            
        sql += " LIMIT 10"
        
        results = conn.execute(text(sql), params).mappings().all()
        duration = (time.time() - start_time) * 1000
    
    return {
        "results": [dict(r) for r in results],
        "meta": {
            "took_ms": round(duration, 2), 
            "quota_used": f"{user['current_usage'] + 1}/{user['request_limit']}"
        }
    }
