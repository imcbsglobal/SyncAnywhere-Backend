from pydantic import BaseModel
from typing import Dict


class DBConnectionParams(BaseModel):
    dsn: str
    userid: str
    password: str


class FetchDataRequest(DBConnectionParams):
    table: str
    columns: str = "*"


class AddDataRequest(DBConnectionParams):
    table: str
    data: Dict[str, str]


class UpdateDataRequest(DBConnectionParams):
    table: str
    where: Dict[str, str]
    updates: Dict[str, str]


class DeleteDataRequest(DBConnectionParams):
    table: str
    where: Dict[str, str]
