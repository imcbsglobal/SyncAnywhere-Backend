# app/db_utils.py

import sqlanydb
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

# Hardcoded DB credentials 
DB_USER = "dba"
DB_PASSWORD = "(*$^)"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_connection():
    try:
        config = load_config()
        dsn = config.get("dsn")

        if not dsn:
            raise Exception("Missing DSN in config.json")

        conn = sqlanydb.connect(
            dsn=dsn,
            userid=DB_USER,
            password=DB_PASSWORD
        )
        return conn

    except Exception as e:
        raise Exception(f"Connection failed: {e}")
