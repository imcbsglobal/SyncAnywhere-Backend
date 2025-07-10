# app/routes/sync.py

from fastapi import APIRouter, HTTPException
from app.schemas import PairCheckInput, LoginInput
from app.db_utils import get_connection, load_config

router = APIRouter()

PAIR_PASSWORD = "IMC_MOBILE_APP_PASSWORD"  # Only mobile app knows this

@router.post("/pair-check")
def pair_check(payload: PairCheckInput):
    config = load_config()
    
    if payload.ip != config.get("ip"):
        raise HTTPException(status_code=403, detail="Invalid IP")

    if payload.password != PAIR_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")

    return {"status": "success", "message": "Paired successfully"}


@router.post("/login")
def login(payload: LoginInput):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM acc_users WHERE username = ? AND password = ?"
        cursor.execute(query, (payload.username, payload.password))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            return {"status": "success", "message": "Login successful"}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
