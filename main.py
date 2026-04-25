from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel, EmailStr
import secrets
import time

app = FastAPI(
    title="India Location API - SaaS Edition",
    description="Professional B2B API with Usage Analytics",
    version="1.1.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- DATABASE CONNECTION ---
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI)

# --- MODELS ---
class UserRegistration(BaseModel):
    organization_name: str
    email: EmailStr
    plan_type: str = "free"

# --- ANALYTICS HELPER ---
def log_usage(api_key: str, endpoint: str, duration: float, status: int):
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO api_usage_logs (api_key, endpoint, response_time_ms, status_code) VALUES (:k, :e, :t, :s)"),
            {"k": api_key, "e": endpoint, "t": duration, "s": status}
        )
        conn.commit()

# --- AUTHENTICATION ---
async def verify_key(api_key: str = Header(None, alias="api-key")):
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key missing")
    
    with engine.connect() as conn:
        query = text("SELECT * FROM api_users WHERE api_key = :k AND is_active = true")
        user = conn.execute(query, {"k": api_key}).mappings().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        if user['current_usage'] >= user['request_limit']:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
        # Update usage count
        conn.execute(text("UPDATE api_users SET current_usage = current_usage + 1 WHERE api_key = :k"), {"k": api_key})
        conn.commit()
        return user

# --- ENDPOINTS ---
@app.get("/")
def health_check():
    return {"status": "Online", "gateway": "SaaS v1.1"}

@app.post("/register")
def register(user: UserRegistration):
    new_key = f"india_loc_{secrets.token_urlsafe(16)}"
    limit = 1000 if user.plan_type == "free" else 10000
    
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO api_users (organization_name, email, api_key, request_limit, plan_type) VALUES (:o, :e, :k, :l, :p)"),
            {"o": user.organization_name, "e": user.email, "k": new_key, "l": limit, "p": user.plan_type}
        )
        conn.commit()
    return {"api_key": new_key, "message": "Save this key! It will not be shown again."}

@app.get("/search")
def search(q: str, user=Depends(verify_key)):
    start = time.time()
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT village_name, taluka_name, pincode FROM villages WHERE village_name ILIKE :q LIMIT 10"),
            {"q": f"%{q}%"}
        ).mappings().all()
    
    duration = (time.time() - start) * 1000
    log_usage(user['api_key'], "/search", duration, 200)
    return {"results": [dict(r) for r in res], "took_ms": round(duration, 2)}
