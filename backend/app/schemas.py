from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class HtmlFileUpload(BaseModel):
    filename: str
    is_locked: bool = False

class HtmlFileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    s3_key: str
    is_locked: bool
    owner_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class HtmlFileLockUpdate(BaseModel):
    is_locked: bool
