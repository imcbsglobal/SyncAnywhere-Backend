import sqlanydb


def get_connection_via_dsn(dsn, userid, password):
    try:
        conn = sqlanydb.connect(
            dsn=dsn,
            userid=userid,
            password=password
        )
        return conn
    except Exception as e:
        raise Exception(f"DSN connection failed: {e}")
