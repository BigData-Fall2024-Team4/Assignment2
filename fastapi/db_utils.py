from fastapi import FastAPI
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('.env')

app = FastAPI()

def load_sql_db_config():
    """Establishes a connection to the GCP Cloud SQL database."""
    try:
        connection = pymysql.connect(
            user=os.getenv("GCP_SQL_USER"),
            password=os.getenv("GCP_SQL_PASSWORD"),
            host=os.getenv("GCP_SQL_HOST"),
            database=os.getenv("GCP_SQL_DATABASE"),
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.Error as e:
        print(f"Error connecting to Cloud SQL: {e}")
        return None

@app.get("/test-sql-connection")
def test_sql_connection():
    connection = load_sql_db_config()
    if connection:
        return {"message": "Successfully connected to Cloud SQL!"}
    else:
        return {"error": "Failed to connect to Cloud SQL."}
    