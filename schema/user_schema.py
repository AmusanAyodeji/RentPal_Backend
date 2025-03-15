from pydantic import BaseModel

class User(BaseModel):
    full_name: str
    email: str
    phone_number: str
    account_type: str
    subscribed: bool = False

class UserCreate(User):
    hashed_password: str