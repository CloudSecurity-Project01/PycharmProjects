import datetime
from passlib.context import CryptContext
from blogueandoAndoAPI.database import database, user_table
from jose import jwt


SECRET_KEY = "123"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"])


def create_access_token(email: str):
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=30)
    jwt_data = {"sub": email, "exp": expire}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_user(email: str):
    query = user_table.select().where(user_table.c.email == email)
    result = await database.fetch_one(query)
    if result:
        return result
