import jwt
from dotenv import load_dotenv
import os
from typing import Annotated
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from schema.user_schema import User, UserCreate
from schema.token_schema import Token, TokenData
from schema.home_schema import Building, BuildingCreate
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

load_dotenv()

buildings = {
    "1":BuildingCreate(description= "Wellmade Home 1",address= "CU",bedroom_no= "4",bathroom_no= "7",furnished= "Fairly Furnished",available_facilities= "24/7 Light, Borehole for Water",interior_features= "Lights, AC",exterior_features= "Trees, Plants",purpose= "sale",price= 100000,payment_frequency= 1,property_type= "bungalow",id=1),
    "2":BuildingCreate(description= "Wellmade Home 2",address= "CU",bedroom_no= "4",bathroom_no= "7",furnished= "Fairly Furnished",available_facilities= "24/7 Light, Borehole for Water",interior_features= "Lights, AC",exterior_features= "Trees, Plants",purpose= "sale",price= 100000,payment_frequency= 1,property_type= "bungalow",id=2),
    "3":BuildingCreate(description= "Wellmade Home 3",address= "CU",bedroom_no= "4",bathroom_no= "7",furnished= "Fairly Furnished",available_facilities= "24/7 Light, Borehole for Water",interior_features= "Lights, AC",exterior_features= "Trees, Plants",purpose= "sale",price= 100000,payment_frequency= 1,property_type= "bungalow",id=3),
    "4":BuildingCreate(description= "Wellmade Home 4",address= "CU",bedroom_no= "4",bathroom_no= "7",furnished= "Fairly Furnished",available_facilities= "24/7 Light, Borehole for Water",interior_features= "Lights, AC",exterior_features= "Trees, Plants",purpose= "sale",price= 100000,payment_frequency= 1,property_type= "bungalow",id=4),
    "5":BuildingCreate(description= "Wellmade Home 5",address= "CU",bedroom_no= "4",bathroom_no= "7",furnished= "Fairly Furnished",available_facilities= "24/7 Light, Borehole for Water",interior_features= "Lights, AC",exterior_features= "Trees, Plants",purpose= "sale",price= 100000,payment_frequency= 1,property_type= "bungalow",id=5)
    }

saved_building = []

saved = {}

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

def hash_password(password):
    return pwd_context.hash(password)

fake_users_db = {
    "landlord@gmail.com":UserCreate(full_name= "string",email= "landlord@gmail.com",phone_number= "12345678901",account_type="Landlord",subscribed= False, hashed_password=hash_password("pw")),
    "agent@gmail.com":UserCreate(full_name= "string",email= "agent@gmail.com",phone_number= "12345678901",account_type="Agent",subscribed= False, hashed_password= hash_password("pw")),
    "user@gmail.com":UserCreate(full_name= "string",email= "user@gmail.com",phone_number= "12345678901",account_type="User",subscribed= False, hashed_password= hash_password("pw"))
    }

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return user_dict

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user
   

@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    global saved_building
    saved_building = []
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if not pwd_context.verify(form_data.password,user_dict.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    return current_user

@app.post("/register/")
def register_user(user_data:UserCreate):

    #look into how to log in with gmail account and x account

    if user_data.email in fake_users_db:
        raise HTTPException(status_code=400, detail="Email Already Exists")
    
    if len(user_data.phone_number) != 11:
        raise HTTPException(status_code=400, detail="Invalid Phone Number")
  
    user_data = UserCreate(
        full_name=user_data.full_name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        account_type=user_data.account_type,
        hashed_password=hash_password(user_data.hashed_password)
    )

    #get library to send otp to users to confirm their email

    fake_users_db[user_data.email]=user_data
    raise HTTPException(status_code=200, detail={"Message":"User Successfully Created"})

@app.patch("/reset_password")
def reset_password(email:str, updated_password:str, confirm_password: str):
    if email not in fake_users_db:
        raise HTTPException(status_code=400, detail="Email Not Found")
    
    user = fake_users_db.get(email)

    #get library to send otp to user to confirm their email

    if not updated_password == confirm_password:
        raise HTTPException(status_code=400, detail="Updated Passwords don't Match")
    elif pwd_context.verify(updated_password,user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is the same as old password")
    
    user.hashed_password = hash_password(updated_password)
    raise HTTPException(status_code=200, detail="Password Successfully Updated")

@app.post("/post_building/")
def post_a_building(building_data:Building, current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.account_type not in ["Landlord", "Agent"]:
        raise HTTPException(status_code=401, detail="Message: Only LandLords Can Post Houses")
    building_dict = BuildingCreate(**building_data.model_dump(), id = len(buildings)+1)
    buildings[building_dict.id] = building_dict
    raise HTTPException(status_code=200, detail=f"Building with Description: {building_data.description} had been created") 
    
@app.get("/buildings")
def show_buildings():
    if len(buildings) == 0:
        return "No buildings in database"
    return buildings

#there is a bug when a user saves buildings and he logs out, when he comes back and saves buildings again, it overwrites the old ones he saved . not too worried cuz it can easily be solved when databses are implemented


@app.post("/buildings/save")
def save_a_building(id:int, current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.account_type != "User":
        raise HTTPException(status_code=401, detail="Message: Only Users can Save Buildings")
    
    if str(id) not in buildings:
        raise HTTPException(status_code=404, detail="Message: Building With that ID not found")
    
    if buildings[str(id)] in saved_building:
        raise HTTPException(status_code=400, detail="Building Already Saved")
    
    saved_building.append(buildings[str(id)])
    saved[current_user.email] = saved_building
    raise HTTPException(status_code=200, detail="Building Successfully saved")

@app.get("/saved")
def show_saved(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.account_type != "User":
        raise HTTPException(status_code=401, detail="Message: Only Users can View Saved Buildings")
    if current_user.email not in saved:
        raise HTTPException(status_code=400,detail="No saved buildings")
    return saved[current_user.email]

