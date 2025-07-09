from fastapi import APIRouter
from app.db_utils import get_connection_via_dsn
from app.schemas import DBConnectionParams, AddDataRequest, UpdateDataRequest, FetchDataRequest, DeleteDataRequest

router = APIRouter()


@router.post("/connect-test")  # CHECK CONNECTION ROUTE
def connect_test(payload: DBConnectionParams):
    try:
        conn = get_connection_via_dsn(
            payload.dsn, payload.userid, payload.password)
        conn.close()
        return {"status": "success", "message": "Connected to DSN successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/fetch-data")  # FETCH DATA ROUTE
def fetch_data(payload: FetchDataRequest):
    try:
        conn = get_connection_via_dsn(
            payload.dsn, payload.userid, payload.password)
        cursor = conn.cursor()
        query = f"SELECT {payload.columns} FROM {payload.table}"
        cursor.execute(query)
        rows = cursor.fetchall()
        column_names = [col[0] for col in cursor.description]
        result = [dict(zip(column_names, row)) for row in rows]
        cursor.close()
        conn.close()
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/add-data")  # ADD DATA ROUTE
def add_data(payload: AddDataRequest):
    try:
        conn = get_connection_via_dsn(
            payload.dsn, payload.userid, payload.password)
        cursor = conn.cursor()

        columns = ', '.join(payload.data.keys())
        placeholders = ', '.join(['?'] * len(payload.data))
        values = list(payload.data.values())
        query = f"INSERT INTO {payload.table} ({columns}) VALUES ({placeholders})"

        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {"status": "success", "message": "Data inserted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.put("/update-data")
def update_data(payload: UpdateDataRequest):
    try:
        conn = get_connection_via_dsn(
            payload.dsn, payload.userid, payload.password)
        cursor = conn.cursor()

        set_clause = ', '.join(f"{k} = ?" for k in payload.updates.keys())
        where_clause = ' AND '.join(f"{k} = ?" for k in payload.where.keys())

        query = f"UPDATE {payload.table} SET {set_clause} WHERE {where_clause}"

        values = list(payload.updates.values()) + list(payload.where.values())
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {"status": "success", "message": "Data updated successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/delete-data")
def delete_data(payload: DeleteDataRequest):
    try:
        conn = get_connection_via_dsn(
            payload.dsn, payload.userid, payload.password)
        cursor = conn.cursor()

        where_clause = ' AND '.join(f"{k} = ?" for k in payload.where.keys())
        values = list(payload.where.values())

        query = f"DELETE FROM {payload.table} WHERE {where_clause}"
        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()

        return {"status": "success", "message": "Data deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
