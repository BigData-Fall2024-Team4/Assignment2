from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import pymysql
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv('.env')

app = FastAPI()

# Function to load SQL database configuration
def load_sql_db_config():
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

# Model for User Registration
class UserRegister(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

    # Custom validation for the password field
    @validator('password')
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError('Password should be at least 8 characters long')
        if not any(char.islower() for char in value):
            raise ValueError('Password should contain at least one lowercase letter')
        if not any(char.isupper() for char in value):
            raise ValueError('Password should contain at least one uppercase letter')
        return value

# Model for User Login
class UserLogin(BaseModel):
    email: EmailStr
    password: constr(min_length=8)

# Hash the password before storing it in the database
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Verify the provided password against the stored hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Register endpoint
@app.post("/register")
def register_user(user: UserRegister):
    connection = load_sql_db_config()  # Assuming load_sql_db_config() is correctly defined elsewhere
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with connection.cursor() as cursor:
            # Check if the user already exists
            check_user_sql = "SELECT * FROM users WHERE email = %s"
            cursor.execute(check_user_sql, (user.email,))
            existing_user = cursor.fetchone()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")

            # Hash the user's password
            hashed_password = hash_password(user.password)

            # Insert the new user with the hashed password
            sql = "INSERT INTO users (email, password) VALUES (%s, %s)"
            cursor.execute(sql, (user.email, hashed_password))
        connection.commit()
        return {"message": "User registered successfully"}

    except pymysql.Error as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

    finally:
        connection.close()

# Login endpoint
@app.post("/login")
def login_user(user: UserLogin):
    connection = load_sql_db_config()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with connection.cursor() as cursor:
            # Retrieve the hashed password from the database
            sql = "SELECT * FROM users WHERE email = %s"
            cursor.execute(sql, (user.email,))
            result = cursor.fetchone()

            if result and verify_password(user.password, result['password']):
                return {"message": "Login successful"}
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
    
    finally:
        connection.close()


class QuestionData(BaseModel):
    task_id: str
    question: str
    file_name: str

def get_gcp_connection():
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
        raise HTTPException(status_code=400, detail=f"Failed to add user history: {str(e)}")
    finally:
        connection.close()

class QuestionData(BaseModel):
    task_id: str
    question: str
    file_name: str

def get_gcp_connection():
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

@app.get("/questions", response_model=List[QuestionData])
async def get_questions(file_type: str = Query('all', enum=['all', 'pdf', 'other']), 
                        dataset: str = Query('both', enum=['validation', 'test', 'both'])):
    """Retrieves question data from the GCP Cloud SQL database."""
    connection = get_gcp_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                tables = []
                if dataset == 'validation' or dataset == 'both':
                    tables.append('validation_cases')
                if dataset == 'test' or dataset == 'both':
                    tables.append('test_cases')
                
                all_data = []
                for table in tables:
                    if file_type == 'pdf':
                        cursor.execute(f"SELECT task_id, question, file_name FROM {table} WHERE file_name LIKE '%.pdf'")
                    elif file_type == 'other':
                        cursor.execute(f"SELECT task_id, question, file_name FROM {table} WHERE file_name NOT LIKE '%.pdf'")
                    else:
                        cursor.execute(f"SELECT task_id, question, file_name FROM {table}")
                    all_data.extend(cursor.fetchall())
            connection.close()
            return all_data
        except pymysql.Error as e:
            raise HTTPException(status_code=500, detail=f"Error fetching data from Cloud SQL: {e}")
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
