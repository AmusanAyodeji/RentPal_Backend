import jwt
from dotenv import load_dotenv
import os
from typing import Annotated
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from schema.user_schema import User, UserCreate
from schema.token_schema import Token, TokenData
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

load_dotenv()

fake_users_db = {}

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

def hash_password(password):
    return pwd_context.hash(password)

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
    return {"Message":{"Email":f"{user.email}","Full Name":f"{user.full_name}"}}
   

@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
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
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user

@app.post("/register/")
def register_user(user_data:UserCreate):

    #look into how to log in with gmail account and x account

    if user_data.email in fake_users_db:
        raise HTTPException(status_code=400, detail="Email Already Exists")
    
    user_data = UserCreate(
        full_name=user_data.full_name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        account_type=user_data.account_type,
        hashed_password=hash_password(user_data.hashed_password)
    )

    #get library to send otp to users to confirm their email

    fake_users_db[user_data.email]=user_data
    return {"Message":"User Successfully Created"}

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
    return "Password Successfully Updated"
    
