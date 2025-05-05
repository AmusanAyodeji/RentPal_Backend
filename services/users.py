from database import cursor, connection
from fastapi import HTTPException
from deps import pwd_context, get_user, hash_password
from schema.user_schema import UserCreate
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

class UserService:
    @staticmethod
    def generate_otp(length=6):
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def send_otp_email(email: str, otp: str):
        sender_email = os.getenv("SMTP_EMAIL")
        sender_password = os.getenv("SMTP_PASSWORD")
        subject = "Your OTP for Verification"
        body = f"Your One-Time Password (OTP) is: {otp}\nIt is valid for 5 minutes."

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
            server.quit()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

    @staticmethod
    def store_otp(email: str, otp: str):
        """Store OTP in the database with a 5-minute expiration."""
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        try:
            cursor.execute(
                """
                INSERT INTO OTPs (email, otp, created_at, expires_at, is_used)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (email, otp, datetime.utcnow(), expires_at, False)
            )
            connection.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to store OTP: {str(e)}")

    @staticmethod
    def verify_otp(email: str, otp: str):
        """Verify the OTP provided by the user."""
        try:
            cursor.execute(
                """
                SELECT otp, expires_at, is_used
                FROM OTPs
                WHERE email = %s AND is_used = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (email, False)
            )
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=400, detail="Invalid or expired OTP")

            stored_otp, expires_at, is_used = result
            if datetime.utcnow() > expires_at:
                raise HTTPException(status_code=400, detail="OTP has expired")
            if stored_otp != otp:
                raise HTTPException(status_code=400, detail="Incorrect OTP")
            if is_used:
                raise HTTPException(status_code=400, detail="OTP already used")

            # Mark OTP as used
            cursor.execute(
                "UPDATE OTPs SET is_used = %s WHERE email = %s AND otp = %s",
                (True, email, otp)
            )
            connection.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to verify OTP: {str(e)}")

    @staticmethod
    def register_user(user_data: UserCreate):
        """Register a new user and send OTP for email verification."""
        user = get_user(user_data.email)
        if user:
            raise HTTPException(status_code=400, detail="Email Already Exists")

        if len(user_data.phone_number) != 11:
            raise HTTPException(status_code=400, detail="Invalid Phone Number")

        if not user_data.password:
            raise HTTPException(status_code=400, detail="Invalid Password")

        # Insert user into database
        try:
            cursor.execute(
                """
                INSERT INTO Users (full_name, email, phone_number, account_type, subscribed, hashed_password)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_data.full_name,
                    user_data.email,
                    user_data.phone_number,
                    user_data.account_type.value,
                    user_data.subscribed,
                    hash_password(user_data.password)
                )
            )
            connection.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to commit to DB: {str(e)}")

        # Generate and send OTP
        otp = UserService.generate_otp()
        UserService.store_otp(user_data.email, otp)
        UserService.send_otp_email(user_data.email, otp)

        return {"message": "User successfully created. Please verify your email with the OTP sent."}

    @staticmethod
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
            raise HTTPException(status_code=400, detail="Unable to change password: "+ str(e))

        raise HTTPException(status_code=200, detail="Password Successfully Updated")


user_crud = UserService()