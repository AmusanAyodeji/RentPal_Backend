from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from schema.token_schema import Token
from schema.user_schema import User, UserCreate
from deps import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from services.users import user_crud
from database import cursor
from datetime import timedelta
from deps import create_access_token, pwd_context, ACCESS_TOKEN_EXPIRE_MINUTES
from schema.login_schema import LoginPayload


usersrouter = APIRouter()



@usersrouter.post("/auth/token", response_model=Token)
def login_oauth(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    cursor.execute("SELECT * FROM Users WHERE email = %s", (form_data.username,))
    db_user = cursor.fetchone()

    if not db_user or not pwd_context.verify(form_data.password, db_user[6]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@usersrouter.post("/auth/login", response_model=Token)
def login(payload: LoginPayload):
    cursor.execute("SELECT * FROM Users WHERE email = %s", (payload.username,))
    db_user = cursor.fetchone()
    
    if not db_user or not pwd_context.verify(payload.password, db_user[6]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": payload.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@usersrouter.get("/users/me")
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

@usersrouter.post("/auth/signup")
def register_user(user_data:UserCreate):
    user_crud.register_user(user_data)


@usersrouter.patch("/reset_password")
def reset_password(email:str, updated_password:str, confirm_password: str):
    user_crud.reset_password(email,updated_password,confirm_password)