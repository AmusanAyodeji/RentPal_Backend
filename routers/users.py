import os
from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from typing import Annotated
from schema.token_schema import Token
from schema.user_schema import User, UserCreate, AccountType, OTPVerifyRequest, LoginRequest
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


@usersrouter.get("/auth/signup")
def google_signup(account_type:AccountType):
    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback"
    )

    authorization_url, state = flow.authorization_url(state=account_type.value)
    return RedirectResponse(authorization_url)

@usersrouter.get("/auth/signin")
def google_login():
    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback"
    )

    authorization_url, state = flow.authorization_url()
    return RedirectResponse(authorization_url)


@usersrouter.get("/auth/callback")
def google_signup_auth_callback(request: Request):
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


    cursor.execute("SELECT * FROM Users WHERE email = %s",(user_info["email"],))
    result = cursor.fetchone()

    if result:
        access_token = create_access_token(data={"sub": user_info["email"]})
        return JSONResponse({
            "access_token": access_token,
            "token_type": "bearer"
        })
    else:
        phone_numbers = people_info.get("phoneNumbers", [])
        phone_number = None
        if phone_numbers:
            phone_number = phone_numbers[0].get("value")
            phone_number = phone_number[:0] + "0" + phone_number[0:]
            cursor.execute("INSERT INTO users(full_name, email, phone_number, subscribed, account_type) VALUES(%s, %s, %s, %s, %s);",
                (user_info["name"], user_info["email"], phone_number, True, account_type))
            connection.commit()
            access_token = create_access_token(data={"sub": user_info["email"]})
            return JSONResponse({
                "access_token": access_token,
                "token_type": "bearer"
            })

        if not phone_number:
            request.session['email'] = user_info["email"]
            cursor.execute("INSERT INTO users(full_name, email, subscribed, account_type) VALUES(%s, %s, %s, %s);",
                (user_info["name"], user_info["email"], True, account_type))
            connection.commit()
            return RedirectResponse(f"/test_webpages/add-phone-number.html?email={user_info['email']}&account_type={account_type}")


@usersrouter.post("/submit-phone-number")
async def submit_phone_number(request: Request, phone_number: str = Form(...)):
    request.session['phone_number'] = phone_number

    email = request.session['email']

    cursor.execute("UPDATE Users SET phone_number = %s WHERE email = %s;",(phone_number, email))
    connection.commit()

    access_token = create_access_token(data={"sub": email})

    return JSONResponse({"access_token": access_token,"token_type": "bearer"})


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

@usersrouter.post("/login/otp")
async def initiate_otp_login(login: LoginRequest):
    return user_crud.login_with_otp(login.email)

@usersrouter.post("/verify-otp")
async def verify_otp(request: OTPVerifyRequest):
    user_crud.verify_otp(request.email, request.otp)
    return {"message": "OTP verified successfully. You are now logged in."}