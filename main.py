from fastapi import FastAPI
from routers.buildings import buildingrouter
from routers.users import usersrouter
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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