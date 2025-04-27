import os
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from typing import Annotated
from schema.token_schema import Token
from schema.user_schema import User, UserCreate, AccountType
from deps import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from services.users import user_crud
from database import cursor, connection
from datetime import timedelta
from deps import create_access_token, pwd_context, ACCESS_TOKEN_EXPIRE_MINUTES
from schema.login_schema import LoginPayload


usersrouter = APIRouter()


os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # ONLY for testing locally

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/user.phonenumbers.read"
]


@usersrouter.get("/auth/login")
def google_login(account_type:AccountType):
    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback"
    )

    authorization_url, state = flow.authorization_url(state=account_type)
    return RedirectResponse(authorization_url)


@usersrouter.get("/auth/callback")
def google_login_auth_callback(request: Request):

    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback"
    )

    account_type = request.query_params.get('state')

    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    session = flow.authorized_session()
    user_info = session.get("https://www.googleapis.com/userinfo/v2/me").json()
    people_info = session.get("https://people.googleapis.com/v1/people/me?personFields=phoneNumbers").json()

    cursor.execute("SELECT * FROM users WHERE email = %s", (user_info["email"],))
    result = cursor.fetchone()

    if not result:
        phone_numbers = people_info.get("phoneNumbers", [])
        phone_number = None
        if phone_numbers:
            phone_number = phone_numbers[0].get("value")
            phone_number = phone_number[:0] + "0" + phone_number[0:]

        # else:
        #     return RedirectResponse(f"/add-phone-number?email={user_info["email"]}")
        
        cursor.execute("INSERT INTO users(full_name,email,phone_number,subscribed,account_type) VALUES(%s,%s,%s,%s,%s)",(user_info["name"],user_info["email"],phone_number,True,account_type))
        connection.commit()

        access_token = create_access_token(data={"sub": user_info["email"]})
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer"
        })



@usersrouter.post("/auth/token", response_model=Token)
def login_authorize_button(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
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