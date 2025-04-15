from pydantic import BaseModel, EmailStr

class User(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    account_type: str
    subscribed: bool = False

class UserCreate(User):
    password: str

class UserDisplay(UserCreate):
    id: str