from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
import os

app = FastAPI(title="India Location API")

# Connection to your Neon Cloud Database
DB_URI = "postgresql://neondb_owner:npg_LHuVs1Od5crb@ep-raspy-union-a47lrzc8.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URI)

@app.get("/")
def home():
    return {"message": "Welcome to the India Location API", "status": "Online"}

@app.get("/states")
def get_states():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM states ORDER BY state_name"))
        return [dict(row._mapping) for row in result]

@app.get("/districts/{state_id}")
def get_districts(state_id: int):
    with engine.connect() as conn:
        query = text("SELECT * FROM districts WHERE state_id = :s_id ORDER BY district_name")
        result = conn.execute(query, {"s_id": state_id})
        districts = [dict(row._mapping) for row in result]
        return districts

@app.get("/villages/{district_id}")
def get_villages(district_id: int):
    with engine.connect() as conn:
        query = text("SELECT * FROM villages WHERE district_id = :d_id ORDER BY village_name")
        result = conn.execute(query, {"d_id": district_id})
        villages = [dict(row._mapping) for row in result]
        return villages
