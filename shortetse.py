import smtplib

sender = "rentpal92@gmail.com"
password = "lrke dhqe zfna yydb"

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(sender, password)
    print("Login successful!")