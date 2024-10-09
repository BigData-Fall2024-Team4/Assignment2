from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, constr, validator
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
