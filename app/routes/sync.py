# app/routes/sync.py
from fastapi import APIRouter, HTTPException, Request, Body
import json
from jose import JWTError, jwt
from app.schemas import PairCheckInput, LoginInput
from app.db_utils import get_connection, load_config
from app.token_utils import create_access_token, SECRET_KEY, ALGORITHM
from datetime import timedelta
import traceback
import subprocess
import os
import psutil
import sys
import logging

router = APIRouter()

PAIR_PASSWORD = "IMC-MOBILE"  # You can change this to whatever password you want

@router.post("/pair-check")
def pair_check(data: dict):
    """
    Pair check endpoint - validates password and starts sync service
    Expected payload: {"ip": "192.168.1.34", "password": "IMC-MOBILE"}
    """
    logging.info(f"📱 Pair check request from: {data}")
    
    # Validate required fields
    if "password" not in data:
        logging.error("❌ Missing password in pair-check request")
        raise HTTPException(status_code=400, detail="Password is required")
    
    # Validate password
    provided_password = data.get("password", "")
    if provided_password != PAIR_PASSWORD:
        logging.error(f"❌ Invalid password provided: '{provided_password}' (expected: '{PAIR_PASSWORD}')")
        raise HTTPException(status_code=401, detail="Invalid password")
    
    logging.info("✅ Password validated successfully")
    
    exe_name = "SyncService.exe"

    # Get correct folder location whether running from .exe or script
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    exe_path = os.path.join(base_dir, exe_name)

    if not os.path.exists(exe_path):
        logging.error(f"❌ SyncService.exe not found at: {exe_path}")
        raise HTTPException(status_code=404, detail="SyncService.exe not found")

    # Check if already running
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and "SyncService.exe" in proc.info['name']:
                logging.info(f"🔄 SyncService already running (PID: {proc.info['pid']})")
                return {
                    "status": "success",
                    "message": "SyncService already running",
                    "pair_successful": True
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Start SyncService
    try:
        subprocess.Popen([exe_path], cwd=base_dir)
        logging.info("✅ SyncService started successfully")
        return {
            "status": "success", 
            "message": "SyncService launched successfully",
            "pair_successful": True
        }
    except Exception as e:
        logging.error(f"❌ Failed to start SyncService: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start sync service: {str(e)}")


@router.post("/login")
def login(payload: LoginInput):
    """
    Login endpoint - validates user credentials
    Expected payload: {"userid": "username", "password": "userpass"}
    """
    logging.info(f"🔐 Login attempt for user: {payload.userid}")
    
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
            logging.info(f"✅ Login successful for user: {payload.userid}")

            access_token = create_access_token(
                data={"sub": payload.userid},
                expires_delta=timedelta(days=7)
            )
            return {
                "status": "success", 
                "message": "Login successful", 
                "user_id": user_id, 
                "token": access_token
            }
        else:
            logging.warning(f"❌ Invalid credentials for user: {payload.userid}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        logging.error(f"❌ Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify-token")
def verify_token(request: Request):
    """Verify JWT token validity"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logging.warning("❌ Token missing in verification request")
        raise HTTPException(status_code=401, detail="Token missing")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userid = payload.get("sub")
        logging.info(f"✅ Token verified for user: {userid}")
        return {"status": "success", "userid": userid}
    except JWTError as e:
        logging.warning(f"❌ Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    

@router.get("/data-download")
def data_download(request: Request):
    """Download data endpoint - requires valid JWT token"""
    logging.info("📥 Data download request received")
    
    # ✅ Step 1: Verify JWT token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logging.warning("❌ Token missing in data download request")
        raise HTTPException(status_code=401, detail="Token missing")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userid = payload.get("sub")
        logging.info(f"✅ Data download authorized for user: {userid}")
    except JWTError:
        logging.warning("❌ Invalid token in data download request")
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

        logging.info(f"✅ Data download successful: {len(master_data)} masters, {len(product_data)} products")
        
        return {
            "status": "success",
            "master_data": master_data,
            "product_data": product_data
        }

    except Exception as e:
        logging.error(f"❌ Data download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/upload-orders")
def upload_orders(request: Request, payload: dict = Body(...)):
    """Upload orders endpoint - requires valid JWT token"""
    logging.info("📤 Orders upload request received")
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logging.warning("❌ Token missing in upload orders request")
        raise HTTPException(status_code=401, detail="Token missing")
        
    token = auth_header.split(" ")[1]

    try:
        decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        userid = decoded_payload.get("sub")
        logging.info(f"✅ Upload orders authorized for user: {userid}")
    except JWTError:
        logging.warning("❌ Invalid token in upload orders request")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        logging.info("🔗 Connecting to database...")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT MAX(slno) FROM acc_purchaseordermaster")
        max_slno = int(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT MAX(orderno) FROM acc_purchaseordermaster")
        max_orderno = int(cursor.fetchone()[0] or 0)

        orders = payload.get("orders", [])
        logging.info(f"📦 Processing {len(orders)} orders...")

        for order in orders:
            # Generate new slno and orderno
            max_slno += 1
            max_orderno += 1
            logging.info(f"📝 Processing Order: slno={max_slno}, orderno={max_orderno}")

            supplier_code = order.get("supplier_code")
            otype = order.get("otype", "O")
            order_userid = order.get("userid")
            orderdate = order.get("order_date")

            cursor.execute("""
                INSERT INTO acc_purchaseordermaster (slno, orderno, supplier, otype, userid, orderdate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (max_slno, max_orderno, supplier_code, otype, order_userid, orderdate))

            cursor.execute("SELECT MAX(slno) FROM acc_purchaseorderdetails")
            max_detail_slno = int(cursor.fetchone()[0] or 0)

            for product in order.get("products", []):
                max_detail_slno += 1
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
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logging.info(f"✅ Orders uploaded successfully: {len(orders)} orders processed")
        return {"status": "success", "message": "Orders uploaded successfully"}

    except Exception as e:
        logging.error(f"❌ Orders upload failed: {str(e)}")
        logging.error("📋 Full error details:", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Test endpoint to check server status
@router.get("/status")
def get_status():
    """Simple status check endpoint"""
    config = load_config()
    return {
        "status": "online",
        "message": "SyncAnywhere server is running",
        "server_ip": config.get("ip", "unknown"),
        "pair_password_hint": f"Password starts with: {PAIR_PASSWORD[:3]}..."
    }