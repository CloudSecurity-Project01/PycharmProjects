from datetime import datetime, timedelta, timezone
import os
from typing import Optional

import jwt
import sqlalchemy as sa
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer
from blogueandoAndoAPI.helpers.database import fetch_one_query
from blogueandoAndoAPI.helpers.database import User as user_table
from passlib.context import CryptContext
from dotenv import load_dotenv

from blogueandoAndoAPI.helpers.database import session

# Load environment variables
load_dotenv()

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Password utilities
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Token creation utilities
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_email_confirmation_token(user_id: int, expires_delta: timedelta = timedelta(hours=1)) -> str:
    to_encode = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_password_reset_token(email: str, expires_delta: timedelta = timedelta(hours=1)) -> str:
    to_encode = {"sub": email, "exp": datetime.now(timezone.utc) + expires_delta}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_email_from_token(token: str):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload)
        if "exp" in payload and datetime.fromtimestamp(payload["exp"], tz=timezone.utc) < datetime.now(timezone.utc):
            return None
        
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    
# User authentication helpers
async def get_user_from_token(token: str) -> Optional[dict]:
    
    try:
        email: str = get_email_from_token(token)

        if not email:
            return None

        query = sa.select(
            user_table.id,
            user_table.name.label("user_name"),
            user_table.email
        ).where(user_table.email == email)

        return fetch_one_query(query)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_user_optional(token: str = Security(oauth2_scheme)) -> Optional[dict]:
    return await get_user_from_token(token)
