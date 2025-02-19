import os
import ssl
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

from blogueandoAndoAPI.helpers.database import database
from blogueandoAndoAPI.routers.user import router as user_router
from blogueandoAndoAPI.routers.post import router as posts_router
from blogueandoAndoAPI.routers.tag import router as tags_router

# Load environment variables
load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL")

origins = [ 
    FRONTEND_URL
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem', password=None)

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
