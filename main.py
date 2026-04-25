from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy import create_engine, text
import os

app = FastAPI(title="India Location API - SaaS Edition")

# Connection to your Neon Cloud
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI)

# --- SECURITY LAYER ---
VALID_API_KEYS = ["capstone_demo_2024", "b2b_client_test"]

def verify_api_key(api_key: str = Header(None)):
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")
    return api_key

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "Welcome to the India Location SaaS API", "status": "Online"}

@app.get("/states", dependencies=[Depends(verify_api_key)])
def get_states():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM states ORDER BY state_name"))
        return [dict(row._mapping) for row in result]

@app.get("/districts/{state_id}", dependencies=[Depends(verify_api_key)])
def get_districts(state_id: int):
    with engine.connect() as conn:
        query = text("SELECT * FROM districts WHERE state_id = :s_id ORDER BY district_name")
        result = conn.execute(query, {"s_id": state_id})
        return [dict(row._mapping) for row in result]

# NEW: Search Endpoint for Autocomplete
@app.get("/search", dependencies=[Depends(verify_api_key)])
def search_location(q: str):
    """Search villages and districts by name for autocomplete menus."""
    if len(q) < 3:
        return {"results": [], "message": "Type at least 3 characters"}
        
    with engine.connect() as conn:
        # Search villages
        v_query = text("SELECT village_name as name, 'village' as type FROM villages WHERE village_name ILIKE :q LIMIT 10")
        villages = conn.execute(v_query, {"q": f"%{q}%"}).mappings().all()
        
        # Search districts
        d_query = text("SELECT district_name as name, 'district' as type FROM districts WHERE district_name ILIKE :q LIMIT 5")
        districts = conn.execute(d_query, {"q": f"%{q}%"}).mappings().all()
        
        return {"query": q, "results": list(villages) + list(districts)}
