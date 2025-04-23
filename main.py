from fastapi import FastAPI
from routers.buildings import buildingrouter
from routers.users import usersrouter

app = FastAPI()

app.include_router(usersrouter,tags=["users"])
app.include_router(buildingrouter,prefix="/buildings",tags=["buildings"])


@app.get('/')
def home():
    return {"message": "welcome to RentPal"}