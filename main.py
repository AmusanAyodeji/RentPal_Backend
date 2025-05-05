import os
from fastapi import FastAPI
from dotenv import load_dotenv
from routers.buildings import buildingrouter
from routers.users import usersrouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")


app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

origins = [
    "http://localhost:3000",
    "https://rent-pal.vercel.app/"
]

app.include_router(usersrouter,tags=["users"])
app.include_router(buildingrouter,prefix="/buildings",tags=["buildings"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def home():
    return {"message": "welcome to RentPal"}

