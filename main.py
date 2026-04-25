from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy import create_engine, text
import os

app = FastAPI(title="India Location API - SaaS Edition")

# --- DATABASE SETUP ---
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI)

# --- SAAS SECURITY LAYER (Dynamic Tracking) ---
def verify_api_key(api_key: str = Header(None)):
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key missing in header")
    
    with engine.connect() as conn:
        # 1. Check if the key exists in our new api_users table
        query = text("SELECT organization_name, plan_type, request_limit, current_usage FROM api_users WHERE api_key = :key")
        user = conn.execute(query, {"key": api_key}).mappings().first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        # 2. Check if they hit their SaaS limit (PRD Criterion 1.3)
        if user['current_usage'] >= user['request_limit']:
            raise HTTPException(status_code=429, detail="Monthly limit reached. Please upgrade your plan.")
        
        # 3. Log the usage (Increment count)
        conn.execute(
            text("UPDATE api_users SET current_usage = current_usage + 1 WHERE api_key = :key"),
            {"key": api_key}
        )
        conn.commit() # Critical for saving the count
        
        return user

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "Welcome to the India Location SaaS API", "status": "Online"}

@app.get("/search")
def search_location(q: str, user_data=Depends(verify_api_key)):
    """Search with SaaS tracking and super-fast Trigram Indexing."""
    if len(q) < 3:
        return {"results": [], "message": "Type at least 3 characters"}
        
    with engine.connect() as conn:
        # Village Search using the GIN index we built
        v_query = text("""
            SELECT v.village_name as name, d.district_name, s.state_name, 'village' as type 
            FROM villages v
            JOIN districts d ON v.district_id = d.district_id
            JOIN states s ON d.state_id = s.state_id
            WHERE v.village_name ILIKE :q LIMIT 10
        """)
        villages = conn.execute(v_query, {"q": f"%{q}%"}).mappings().all()
        
        return {
            "query": q,
            "organization": user_data['organization_name'],
            "usage_stats": f"{user_data['current_usage'] + 1} / {user_data['request_limit']}",
            "results": villages
        }
