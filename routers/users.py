import os
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from typing import Annotated
from schema.token_schema import Token
from schema.user_schema import User, UserCreate, AccountType
from schema.otp_schema import OTPVerifyRequest
from deps import get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from services.users import user_crud
from database import db_pool
from datetime import timedelta
from deps import create_access_token, pwd_context, ACCESS_TOKEN_EXPIRE_MINUTES
from schema.login_schema import LoginPayload

usersrouter = APIRouter()

# Allow HTTP in development (never use in prod)
# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/user.phonenumbers.read"
]

def create_google_flow():
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/callback")
    return Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

@usersrouter.get("/auth/signup")
def google_signup(state: AccountType = Query(...)):  # changed from account_type
    flow = create_google_flow()
    auth_url, _ = flow.authorization_url(state=state.value)
    return RedirectResponse(auth_url)

@usersrouter.get("/auth/signin")
def google_login():
    flow = create_google_flow()
    auth_url, _ = flow.authorization_url()
    return RedirectResponse(auth_url)

@usersrouter.get("/auth/callback")
def google_signup_or_signin_auth_callback(request: Request):
    flow = create_google_flow()
    account_type = request.query_params.get("state")  # same param passed earlier

    try:
        flow.fetch_token(authorization_response=str(request.url))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth token fetch failed: {e}")

    credentials = flow.credentials
    session = flow.authorized_session()

    try:
        user_info = session.get("https://www.googleapis.com/userinfo/v2/me").json()
        people_info = session.get("https://people.googleapis.com/v1/people/me?personFields=phoneNumbers").json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user info: {e}")

    # Check if user exists
    conn = db_pool.getconn()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = %s", (user_info["email"],))
    result = cursor.fetchone()
    cursor.close()
    db_pool.putconn(conn)

    if not result:
        phone_numbers = people_info.get("phoneNumbers", [])
        phone_number = phone_numbers[0].get("value") if phone_numbers else None
        if phone_number:
            phone_number = "0" + phone_number  # ensure Nigerian-like formatting?

        conn = db_pool.getconn()
        conn.autocommit = True
        cursor = conn.cursor()
        if phone_number:
            cursor.execute(
                "INSERT INTO users(full_name, email, phone_number, subscribed, account_type) VALUES(%s, %s, %s, %s, %s);",
                (user_info["name"], user_info["email"], phone_number, True, account_type))
        else:
            cursor.execute(
                "INSERT INTO users(full_name, email, subscribed, account_type) VALUES(%s, %s, %s, %s);",
                (user_info["name"], user_info["email"], True, account_type))
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)

    access_token = create_access_token(data={"sub": user_info["email"]})
    return JSONResponse({
        "access_token": access_token,
        "token_type": "bearer"
    })

@usersrouter.post("/auth/token", response_model=Token)
def login_authorize_button(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    conn = db_pool.getconn()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = %s", (form_data.username,))
    db_user = cursor.fetchone()

    if not db_user or not pwd_context.verify(form_data.password, db_user[6]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)
    cursor.close()
    db_pool.putconn(conn)
    return Token(access_token=access_token, token_type="bearer")

@usersrouter.post("/auth/login", response_model=Token)
def login(payload: LoginPayload):
    conn = db_pool.getconn()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = %s", (payload.username,))
    db_user = cursor.fetchone()

    if not db_user or not pwd_context.verify(payload.password, db_user[6]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": payload.username}, expires_delta=access_token_expires)
    cursor.close()
    db_pool.putconn(conn)
    return Token(access_token=access_token, token_type="bearer")

@usersrouter.get("/users/me")
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

@usersrouter.post("/auth/signup")
def register_user(user_data: UserCreate):
    user_crud.register_user(user_data)

@usersrouter.patch("/reset_password")
def reset_password(email: str, updated_password: str, confirm_password: str):
    user_crud.reset_password(email, updated_password, confirm_password)

@usersrouter.post("/verify-otp")
async def verify_otp(request: OTPVerifyRequest):
    user_crud.verify_otp(request.email, request.otp)
    access_token = create_access_token(data={"sub": request.email})
    return JSONResponse({
        "access_token": access_token,
        "token_type": "bearer"
    })