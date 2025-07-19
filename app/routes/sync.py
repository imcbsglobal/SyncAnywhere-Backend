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
        
        query = "SELECT id, pass FROM acc_users WHERE id = ? AND pass = ?"
        cursor.execute(query, (payload.userid, payload.password))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            user_id = user[0]

            access_token = create_access_token(
                data={"sub": payload.userid},
                expires_delta=timedelta(days=7)
            )
            return {"status": "success", "message": "Login successful", "user_id": user_id, "token": access_token}
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
    

 
@router.get("/data-download")
def data_download(request: Request):
    # ✅ Step 1: Verify JWT token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token missing")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ✅ Step 3: Fetch acc_master data
        cursor.execute("SELECT code, name, place FROM acc_master WHERE super_code = 'SUNCR'")
        master_rows = cursor.fetchall()
        master_data = [
            {
                "code": row[0],
                "name": row[1],
                "place": row[2]
            }
            for row in master_rows
        ]

        cursor.execute("""
            SELECT 
                p.code,
                p.name,
                pb.barcode,
                pb.quantity,
                pb.salesprice,
                pb.bmrp,
                pb.cost
            FROM 
                acc_product p
            LEFT JOIN 
                acc_productbatch pb
            ON 
                p.code = pb.productcode
        """)
        product_rows = cursor.fetchall()
        product_data = [
            {
                "code": row[0],
                "name": row[1],
                "barcode": row[2],
                "quantity": row[3],
                "salesprice": row[4],
                "bmrp": row[5],
                "cost": row[6]
            }
            for row in product_rows
        ]

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "master_data": master_data,
            "product_data": product_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
