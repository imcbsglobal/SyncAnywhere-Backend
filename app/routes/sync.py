# app/routes/sync.py
from fastapi import APIRouter, HTTPException, Request, Body
from jose import JWTError, jwt
from app.schemas import PairCheckInput, LoginInput
from app.db_utils import get_connection, load_config
from app.token_utils import create_access_token, SECRET_KEY, ALGORITHM
from datetime import timedelta
import traceback

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


@router.post("/upload-orders")
def upload_orders(request: Request, payload: dict = Body(...)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token missing")
    token = auth_header.split(" ")[1]

    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        print("Connecting to DB...")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT MAX(slno) FROM acc_purchaseordermaster")
        max_slno = int(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT MAX(orderno) FROM acc_purchaseordermaster")
        max_orderno = int(cursor.fetchone()[0] or 0)

        print(" Processing payload orders...")

        orders = payload.get("orders", [])

        print(f"Received {len(orders)} orders")
        for order in orders:
            # Generate new slno and orderno
            max_slno += 1
            max_orderno += 1
            print(f"Processing Order: slno={max_slno}, orderno={max_orderno}")

            supplier_code = order.get("supplier_code")
            otype = order.get("otype", "O")
            userid = order.get("userid")
            orderdate = order.get("order_date")

            print("Inserting into acc_purchaseordermaster...")
            cursor.execute("""
                INSERT INTO acc_purchaseordermaster (slno, orderno, supplier, otype, userid, orderdate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (max_slno, max_orderno, supplier_code, otype, userid, orderdate))

            print("Getting max detail slno...")
            cursor.execute("SELECT MAX(slno) FROM acc_purchaseorderdetails")
            max_detail_slno = int(cursor.fetchone()[0] or 0)

            for product in order.get("products", []):
                max_detail_slno += 1
                print(f"Inserting product: {product}")
                cursor.execute("""
                    INSERT INTO acc_purchaseorderdetails 
                    (masterslno, slno, barcode, qty, rate, mrp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    max_slno,
                    max_detail_slno,
                    product.get("barcode"),
                    product.get("quantity"),
                    product.get("rate"),
                    product.get("mrp")
                ))
        
        print("Committing transaction...")
        conn.commit()
        cursor.close()
        conn.close()
        
        print("Orders uploaded successfully")
        return {"status": "success", "message": "Orders uploaded successfully"}

    except Exception as e:
        print("❌ Exception occurred while uploading orders:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")