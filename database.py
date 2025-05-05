import os
from psycopg2.pool import ThreadedConnectionPool
import psycopg2
import time
from dotenv import load_dotenv

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
db_pool = None

def init_db_connection(max_retries=5, initial_delay=2):
    """Initialize a ThreadedConnectionPool for PostgreSQL."""
    global db_pool
    attempt = 0
    delay = initial_delay
    while attempt < max_retries:
        try:
            db_pool = ThreadedConnectionPool(
                minconn=1, 
                maxconn=10,  
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME,
                options="-c idle_in_transaction_session_timeout=10min" 
            )
            conn = db_pool.getconn()
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()
            cursor.close()
            db_pool.putconn(conn)
            return db_pool
        except psycopg2.OperationalError as e:
            attempt += 1
            if attempt == max_retries:
                raise Exception("Unable to initialize database pool")
            time.sleep(delay)
            delay *= 2
        except Exception as e:
            raise

try:
    db_pool = init_db_connection()
except Exception as e:
    raise