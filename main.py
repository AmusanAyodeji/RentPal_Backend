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

#---------------------------------Added to test google sign in flow-------------------------------
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Serve static files from the "static" directory
app.mount("/test_webpages", StaticFiles(directory="test_webpages"), name="static")

# You can also define a route to directly serve the HTML page, if needed
@app.get("/test_webpages/add-phone-number.html", response_class=HTMLResponse)
async def get_phone_number_page():
    with open("test_webpages/add-phone-number.html") as f:
        return HTMLResponse(content=f.read())    

#--------------------------------------------------------------------------------------------------


@app.get('/')
def home():
    return {"message": "welcome to RentPal"}

