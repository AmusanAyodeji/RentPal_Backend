import jwt
from dotenv import load_dotenv
import os
import psycopg2
from typing import Annotated
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from schema.user_schema import User, UserCreate
from schema.token_schema import Token, TokenData
from schema.home_schema import BuildingCreate, Building, BuildingDisplay
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")
    cursor = connection.cursor()
except Exception as e:
    print(f"Failed to connect: {e}")

# in use

building = {}

#stops here


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI()

def hash_password(password):
    return pwd_context.hash(password)

#convert from dictionary to database

def get_user(username: str):
    cursor.execute("SELECT * FROM Users WHERE email = %s",(username,))
    user = cursor.fetchone()
    if user:
        user = User(
            id = user[0],
            full_name = user[1],
            email = user[2],
            phone_number = user[3],
            account_type = user[4],
            subscribed = user[5]
        )
        return user

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
    
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    return user
   

#finished auth/login
@app.post("/auth/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    cursor.execute("SELECT * FROM Users WHERE email = %s", (form_data.username,))
    db_user = cursor.fetchone()
    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if not pwd_context.verify(form_data.password,db_user[6]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

#finsihed users/me
@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)]
):
    return current_user

#finished /auth/signup
@app.post("/auth/signup/")
def register_user(user_data:UserCreate):

    #look into how to log in with gmail account and x account
    user = get_user(user_data.email)
    if user:
        raise HTTPException(status_code=400, detail="Email Already Exists")

    if len(user_data.phone_number) != 11:
        raise HTTPException(status_code=400, detail="Invalid Phone Number")

    try:
        cursor.execute("INSERT INTO Users(full_name,email,phone_number,account_type,subscribed,hashed_password) VALUES(%s, %s, %s, %s, %s, %s);",(user_data.full_name,user_data.email,user_data.phone_number,user_data.account_type,user_data.subscribed,hash_password(user_data.password)))
        connection.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to commit to DB: "+e)

    #get library to send otp to users to confirm their email

    raise HTTPException(status_code=200, detail={"Message":"User Successfully Created"})

#finished /reset_password
@app.patch("/reset_password/")
def reset_password(email:str, updated_password:str, confirm_password: str):

    cursor.execute("SELECT * FROM Users WHERE email = %s",(email,))
    user = cursor.fetchone()

    if user is None:
        raise HTTPException(status_code=400, detail="Email Not Found")

    #get library to send otp to user to confirm their email

    if not updated_password == confirm_password:
        raise HTTPException(status_code=400, detail="Updated Passwords don't Match")
    elif pwd_context.verify(updated_password,user[6]):
        raise HTTPException(status_code=400, detail="Password is the same as old password")
    
    try:
        cursor.execute("UPDATE Users SET hashed_password = %s WHERE email = %s",(hash_password(updated_password),email))
        connection.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Unable to change password: "+e)
    
    raise HTTPException(status_code=200, detail="Password Successfully Updated")

#finished /post_building/
@app.post("/post_building/")
def post_a_building(building_data:BuildingCreate, current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.account_type not in ["Landlord", "Agent"]:
        raise HTTPException(status_code=401, detail="Message: Only LandLords Can Post Houses")
    try:
        cursor.execute("INSERT INTO Buildings(description,address,bedroom_no,bathroom_no,furnished,available_facilities,interior_features,exterior_features,purpose,price,payment_frequency,property_type) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(building_data.description,building_data.address,building_data.bedroom_no,building_data.bathroom_no,building_data.furnished,building_data.available_facilities,building_data.interior_features,building_data.exterior_features,building_data.purpose,building_data.price,building_data.payment_frequency,building_data.property_type))
        connection.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Unable to add building to DB"+e)

    raise HTTPException(status_code=200, detail=f"Building with Description: {building_data.description} had been created") 
    
#finished /buildings/
@app.get("/buildings/")
def show_buildings():
    cursor.execute("SELECT * FROM Buildings")
    buildings = cursor.fetchall()

    if not buildings:
        raise HTTPException(status_code=404, detail="No building found in DB")
    
    building_list = []
    for b in buildings:
        building_list.append(BuildingDisplay(
            description = b[1],
            address = b[2],
            bedroom_no = b[3],
            bathroom_no = b[4],
            furnished = b[5],
            available_facilities = b[6],
            interior_features = b[7],
            exterior_features = b[8],
            purpose = b[9],
            price = b[10],
            payment_frequency = b[11],
            property_type = b[12]
        ))

    return building_list

#finished /buildings/save
@app.post("/buildings/save")
def save_a_building(id:str, current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.account_type != "User":
        raise HTTPException(status_code=401, detail="Message: Only Users can Save Buildings")

    cursor.execute("SELECT * FROM buildings WHERE id = %s",(id,))
    found_building = cursor.fetchone()

    if found_building is None:
        raise HTTPException(status_code=404, detail="Message: Building With that ID not found")
    
    cursor.execute("SELECT * FROM saved_buildings WHERE building_id = %s AND user_email = %s",(id,current_user.email))
    saved_building = cursor.fetchone()

    if saved_building:
        raise HTTPException(status_code=400, detail="Building Already Saved")
    
    try:
        cursor.execute("INSERT INTO saved_buildings(user_email,building_id) VALUES(%s, %s)",(current_user.email,id))
        connection.commit()
    except Exception as e:
        raise HTTPException(status_code=400,detail="Unable to add to DB: "+e)
    
    raise HTTPException(status_code=200, detail="Building Successfully saved")


@app.get("/saved")
def show_saved(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.account_type != "User":
        raise HTTPException(status_code=401, detail="Message: Only Users can View Saved Buildings")
    
    cursor.execute("SELECT b.* FROM Buildings b JOIN saved_buildings sb ON b.id = sb.building_id WHERE sb.user_email = %s", (current_user.email,))

    saved_buildings = cursor.fetchall()

    if not  saved_buildings:
        raise HTTPException(status_code=400,detail="No saved buildings")
    
    saved_list = []
    for building in saved_buildings:
        saved_list.append(BuildingDisplay(
            description = building[1],
            address = building[2],
            bedroom_no = building[3],
            bathroom_no = building[4],
            furnished = building[5],
            available_facilities = building[6],
            interior_features = building[7],
            exterior_features = building[8],
            purpose = building[9],
            price = building[10],
            payment_frequency = building[11],
            property_type = building[12]
        ))

    return saved_list