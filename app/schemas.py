# app/schemas.py

from pydantic import BaseModel
from typing import Optional

class PairCheckInput(BaseModel):
    ip: str
    password: str

class LoginInput(BaseModel):
    userid: str
    password: str

class TokenResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[str] = None
    token: Optional[str] = None

class PairCheckResponse(BaseModel):
    status: str
    message: str
    pair_successful: bool