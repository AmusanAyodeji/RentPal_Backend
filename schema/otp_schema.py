from pydantic import BaseModel, EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str