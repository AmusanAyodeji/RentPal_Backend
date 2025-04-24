from database import cursor, connection
from fastapi import HTTPException
from deps import pwd_context, get_user, hash_password
from schema.user_schema import UserCreate



class UserService:

    @staticmethod
    def register_user(user_data:UserCreate):
        #look into how to log in with gmail account and x account
        user = get_user(user_data.email)
        if user:
            raise HTTPException(status_code=400, detail="Email Already Exists")

        if len(user_data.phone_number) != 11:
            raise HTTPException(status_code=400, detail="Invalid Phone Number")

        try:
            cursor.execute("INSERT INTO Users(full_name,email,phone_number,account_type,subscribed,hashed_password) VALUES(%s, %s, %s, %s, %s, %s);",(user_data.full_name,user_data.email,user_data.phone_number,user_data.account_type,user_data.subscribed,hash_password(user_data.password)))
            connection.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Failed to commit to DB: "+e)

        #get library to send otp to users to confirm their email

        raise HTTPException(status_code=200, detail={"Message":"User Successfully Created"})

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
            raise HTTPException(status_code=400, detail="Unable to change password: "+e)

        raise HTTPException(status_code=200, detail="Password Successfully Updated")


user_crud = UserService()