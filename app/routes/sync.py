# app/routes/sync.py

from fastapi import APIRouter, HTTPException, Request
from jose import JWTError, jwt
from app.schemas import PairCheckInput, LoginInput
from app.db_utils import get_connection, load_config
from app.token_utils import create_access_token, SECRET_KEY, ALGORITHM
from datetime import timedelta

router = APIRouter()

PAIR_PASSWORD = "IMC-MOBILE" 

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
        
        query = "SELECT * FROM acc_users WHERE id = ? AND pass = ?"
        cursor.execute(query, (payload.userid, payload.password))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            access_token = create_access_token(
                data={"sub": payload.userid},
                expires_delta=timedelta(days=7)
            )
            return {"status": "success", "message": "Login successful", "token": access_token}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify-token")
def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token missing")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userid = payload.get("sub")
        return {"status": "success", "userid": userid}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")