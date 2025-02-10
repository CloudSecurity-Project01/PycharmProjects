from contextlib import asynccontextmanager
from fastapi import FastAPI
from blogueandoAndoAPI.routers.user import router as user_router
from blogueandoAndoAPI.routers.post import router as posts_router
from blogueandoAndoAPI.routers.tag import router as tags_router
from blogueandoAndoAPI.database import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()


app = FastAPI(lifespan=lifespan)


app.include_router(user_router)
app.include_router(posts_router)
app.include_router(tags_router)
