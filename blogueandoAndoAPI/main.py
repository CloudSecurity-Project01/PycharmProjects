from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from blogueandoAndoAPI.routers.user import router as user_router
from blogueandoAndoAPI.routers.post import router as posts_router
from blogueandoAndoAPI.routers.tag import router as tags_router
from blogueandoAndoAPI.helpers.database import database

origins = [
    "http://localhost:3000"
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()


app = FastAPI(lifespan=lifespan)

app.include_router(user_router)
app.include_router(posts_router)
app.include_router(tags_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
