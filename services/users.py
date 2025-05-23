from fastapi import HTTPException
from fastapi.responses import JSONResponse
from deps import pwd_context, get_user, hash_password
from database import db_pool
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

        plain_text = f"Your One-Time Password (OTP) is: {otp}\nIt is valid for 5 minutes."

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <h2 style="color: #333;">Email Verification</h2>
                    <p style="font-size: 16px;">Use the following OTP to verify your email address:</p>
                    <p style="font-size: 24px; font-weight: bold; color: #007BFF;">{otp}</p>
                    <p style="font-size: 14px; color: #666;">This code is valid for 5 minutes.</p>
                </div>
            </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg['Reply-To'] = sender_email
        msg.add_header('MIME-Version', '1.0')
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

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
        conn = db_pool.getconn()
        conn.autocommit = True
        cursor = conn.cursor()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        try:
            cursor.execute(
                """
                INSERT INTO OTPs (email, otp, created_at, expires_at, is_used)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (email, otp, datetime.utcnow(), expires_at, False)
            )
            conn.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to store OTP: {str(e)}")

    @staticmethod
    def verify_otp(email: str, otp: str):
        conn = db_pool.getconn()
        conn.autocommit = True
        cursor = conn.cursor()
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
            conn.commit()
            cursor.close()
            db_pool.putconn(conn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to verify OTP: {str(e)}")

    @staticmethod
    def register_user(user_data: UserCreate):
        conn = db_pool.getconn()
        conn.autocommit = True
        cursor = conn.cursor()
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
            conn.commit()
            cursor.close()
            db_pool.putconn(conn)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to commit to DB: {str(e)}")

        # Generate and send OTP
        otp = UserService.generate_otp()
        UserService.store_otp(user_data.email, otp)
        UserService.send_otp_email(user_data.email, otp)

        return {"message": "User successfully created. Please verify your email with the OTP sent."}

    @staticmethod
    def reset_password(email:str, updated_password:str, confirm_password: str):
        conn = db_pool.getconn()
        conn.autocommit = True
        cursor = conn.cursor()
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
            conn.commit()
            cursor.close()
            db_pool.putconn(conn)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Unable to change password: "+ str(e))

        raise HTTPException(status_code=200, detail="Password Successfully Updated")


user_crud = UserService()