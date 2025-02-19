from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from starlette.responses import HTMLResponse
from datetime import timedelta
import jwt

from blogueandoAndoAPI.models.user import AuthenticationIn, Authentication, Token
from blogueandoAndoAPI.helpers.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_email_confirmation_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM
)
from blogueandoAndoAPI.helpers.database import user_table, database
from blogueandoAndoAPI.helpers.email import send_confirmation_email
import os

# Router initialization
router = APIRouter()
templates = Jinja2Templates(directory="blogueandoAndoAPI/templates")

# Load frontend URL
FRONTEND_URL = os.getenv("FRONTEND_URL")
LOGIN_URL = f"{FRONTEND_URL}/login"


# User Registration
@router.post("/register")
async def register(user: Authentication, request: Request):
    try:
        async with database.transaction():
            existing_user = await database.fetch_one(
                user_table.select().where(user_table.c.email == user.email)
            )

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe una cuenta con este correo electrónico"
                )

            hashed_password = get_password_hash(user.password)

            await database.execute(
                user_table.insert().values(
                    name=user.name, email=user.email, password=hashed_password, is_verified=False
                )
            )

            new_user = await database.fetch_one(
                user_table.select().where(user_table.c.email == user.email)
            )
            new_user_id = new_user["id"]

            confirmation_token = create_email_confirmation_token(new_user_id)
            verification_link = f"{str(request.base_url)}confirm_email?token={confirmation_token}"

            try:
                send_confirmation_email(user.email, user.name, verification_link)
            except Exception as e:
                print(e)
                raise HTTPException(status_code=500, detail="Error al enviar el correo de confirmación")

        return {"message": "Revisa tu bandeja de entrada para activar tu cuenta"}

    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado")


# User Login
@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: AuthenticationIn):
    user = await database.fetch_one(
        user_table.select().where(user_table.c.email == form_data.email)
    )

    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva. Primero confirma el correo registrado.",
        )

    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=timedelta(minutes=30))
    
    return {"access_token": access_token, "token_type": "bearer"}


# Email Confirmation
@router.get("/confirm_email", response_class=HTMLResponse)
async def confirm_email(request: Request, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El token no es válido")

        user = await database.fetch_one(user_table.select().where(user_table.c.id == user_id))

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        await database.execute(
            user_table.update().where(user_table.c.id == user_id).values(is_verified=True)
        )

        return templates.TemplateResponse(
            "confirmation_success.html",
            {"request": request, "message": "Tu correo ha sido confirmado correctamente", "login_url": LOGIN_URL}
        )

    except jwt.PyJWTError:
        return templates.TemplateResponse(
            "confirmation_failure.html",
            {"request": request, "message": "El token no es válido o ha expirado", "resend_email_url": f"{request.base_url}resend_email"}
        )


# Resend Confirmation Email
@router.get("/resend_email")
async def resend_email(request: Request, user_email: str):
    user = await database.fetch_one(user_table.select().where(user_table.c.email == user_email))

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    confirmation_token = create_email_confirmation_token(user["id"])
    verification_link = f"{str(request.base_url)}confirm_email?token={confirmation_token}"

    try:
        send_confirmation_email(user["email"], user["name"], verification_link)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error al enviar el correo de confirmación")

    return templates.TemplateResponse(
        "confirmation_success.html",
        {"request": request, "message": "Correo de confirmación reenviado correctamente", "login_url": LOGIN_URL}
    )


# Get Current User Data
@router.get("/user")
async def get_user_data(current_user: dict = Depends(get_current_user)):
    return current_user
