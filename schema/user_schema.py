from pydantic import BaseModel, EmailStr
from enum import Enum

class AccountType(str, Enum):
    user = "User"
    landlord = "Landlord"
    agent = "Agent"

class AccountBase(BaseModel):
    account_type: AccountType

class User(AccountBase):
    full_name: str
    email: EmailStr
    phone_number: str
    subscribed: bool = False

class UserCreate(User):
    password: str

class UserDisplay(UserCreate):
    id: str

class OTPVerifyRequest(BaseModel):
    email: str
    otp: str

class LoginRequest(BaseModel):
    email: str