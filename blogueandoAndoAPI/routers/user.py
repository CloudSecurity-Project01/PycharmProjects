from fastapi import APIRouter,  HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from blogueandoAndoAPI.models.user import AuthenticationIn, Authentication, Token
from blogueandoAndoAPI.helpers.security import get_password_hash, verify_password, create_access_token, create_email_confirmation_token, get_current_user
from blogueandoAndoAPI.helpers.database import user_table, database
from blogueandoAndoAPI.helpers.email import send_confirmation_email
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse
from datetime import timedelta
from dotenv import load_dotenv
import jwt
import os

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="blogueandoAndoAPI\\templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
FRONTEND_URL = os.getenv("FRONTEND_URL")
login_url = f"{FRONTEND_URL}/login"

@router.post("/register")
async def register(user: Authentication, request: Request):
    try:
        async with database.transaction():
            # Check if email already exists
            query = user_table.select().where(user_table.c.email == user.email)
            existing_user = await database.fetch_one(query)

            if existing_user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe una cuenta con este correo electrónico")

            hashed_password = get_password_hash(user.password)

            query = user_table.insert().values(
                name=user.name,
                email=user.email,
                password=hashed_password,
                is_verified=False
            )
            await database.execute(query)

            # Get the newly inserted user
            query = user_table.select().where(user_table.c.email == user.email)
            new_user = await database.fetch_one(query)
            new_user_id = new_user['id']

            # Generate confirmation token
            confirmation_token = create_email_confirmation_token(new_user_id)
            verification_link = f"{str(request.base_url)}confirm_email?token={confirmation_token}"

            # Send confirmation email
            try:
                send_confirmation_email(user.email, user.name, verification_link)
            except Exception as e:
                print(e)
                raise HTTPException(status_code=500, detail="Error al enviar el correo de confirmación")

        return {"message": "Revisa tu bandeja de entrada para activar tu cuenta"}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado")



@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: AuthenticationIn):
    query = user_table.select().where(user_table.c.email == form_data.email)
    user = await database.fetch_one(query)
    
    if user is None or not verify_password(form_data.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user['is_verified']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta inactiva. Primero confirma el correo registrado.",
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user['email']}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/confirm_email", response_class=HTMLResponse)
async def confirm_email(request: Request, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El token no es válido")

        query = user_table.select().where(user_table.c.id == user_id)
        user = await database.fetch_one(query)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        update_query = user_table.update().where(user_table.c.id == user_id).values(is_verified=True)
        await database.execute(update_query)

        return templates.TemplateResponse("confirmation_success.html", {"request": request, "message": "Tu correo ha sido confirmado correctamente", "login_url": login_url})
    
    except jwt.PyJWTError as e:
        print(e)
        resend_email_url = f"{str(request.base_url)}resend_email"
        return templates.TemplateResponse("confirmation_failure.html", {"request": request, "message": "El token no es válido o ha expirado", "resend_email_url": resend_email_url})

@router.get("/resend_email")
async def resend_email(request: Request, user_email: str):
    query = user_table.select().where(user_table.c.email == user_email)
    user = await database.fetch_one(query)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    confirmation_token = create_email_confirmation_token(user.id)
    verification_link = f"{str(request.base_url)}confirm_email?token={confirmation_token}"
    
    try:
        send_confirmation_email(user.email,user.name, verification_link)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error al enviar el correo de confirmación")

    return templates.TemplateResponse("confirmation_success.html", {"request": request, "message": "Correo de confirmación reenviado correctamente", "login_url": login_url})

@router.get("/user")
async def get_user_data(current_user: dict = Depends(get_current_user)):
    # `current_user` will be extracted from the JWT token
    return current_user
