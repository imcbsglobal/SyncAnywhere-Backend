# app/schemas.py

from pydantic import BaseModel

class PairCheckInput(BaseModel):
    ip: str
    password: str

class LoginInput(BaseModel):
    userid: str
    password: str
