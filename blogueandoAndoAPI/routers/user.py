from fastapi import APIRouter,  HTTPException, status
from blogueandoAndoAPI.models.user import UserIn, User, AuthenticationIn, Authentication
from blogueandoAndoAPI.security import get_user, get_password_hash
from blogueandoAndoAPI.database import user_table, database


router = APIRouter()


@router.post("/register", status_code=201)
async def register(user: UserIn):
    if await get_user(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email already exist"
        )
    hashed_password = get_password_hash(user.password)
    query = user_table.insert().values(email=user.email, password=hashed_password, name=user.name)
    await database.execute(query)
    return {"detail": "User created."}


@router.get("/login", response_model=Authentication)
async def authenticate(login: AuthenticationIn):
    for u in user_table.values():
        user = User.model_validate(u)
        if user.password == login.password and user.email == login.email:
            return user
    raise HTTPException(status_code=404, detail="User not found")
