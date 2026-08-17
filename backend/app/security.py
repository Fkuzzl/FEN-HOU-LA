from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, Request, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def make_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": expires}, settings.jwt_secret, algorithm="HS256")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="請先登入")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = payload.get("sub")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="登入已失效") from exc
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="找不到使用者")
    if user.is_disabled:
        raise HTTPException(status_code=403, detail="帳戶已停用")
    return user
