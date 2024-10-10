from fastapi import FastAPI,APIRouter, HTTPException, Query, Depends, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List, Optional
from pydantic import BaseModel, EmailStr, constr, validator
import pymysql
import os
from dotenv import load_dotenv
import bcrypt
import jwt
from datetime import datetime, timedelta
import logging
from google.cloud import storage
from google.oauth2 import service_account
import openai
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = FastAPI()
router = APIRouter()

# JWT settings
openai.api_key = os.getenv("OPENAI_API_KEY")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# GCP bucket settings
TXT_BUCKET_NAME= os.getenv("TXT_BUCKET_NAME")


# Google Cloud Storage client setup
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    storage_client = storage.Client(credentials=credentials)
else:
    storage_client = storage.Client()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Model for submitting answers
class SubmitAnswerRequest(BaseModel):
    question: str
    processed_content: str
    api: str  # Indicates which API (PyPDF or Azure) is used
    file_name: str

def get_file_from_gcp(bucket_name: str, file_name: str) -> str:
    try:
        # List of folders to search in
        folders = ['test', 'validation']
        
        # Iterate through each folder to find the file
        for folder in folders:
            blob_path = f"{folder}/{file_name}"
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            if blob.exists():
                # Download the content as text if the file is found
                content = blob.download_as_text()
                return content

        # If the file is not found in any of the folders, raise an error
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found in 'test' or 'validation' folders.")
    
    except Exception as e:
        logger.error(f"Failed to fetch file from GCP bucket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving file from GCP Storage: {str(e)}")


async def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/submit_answer")
async def submit_answer(
    request: SubmitAnswerRequest,
    # token: str = Depends(get_current_user)
):
    file_name1 = Path(request.file_name).stem
    try:
        # Determine the processed file name based on the API
        # return request

        if request.api.lower() == "pypdf":
            processed_file_name = f"{file_name1}.txt"
        elif request.api.lower() == "azure":
            processed_file_name = f"{file_name1}_azure.txt"
        else:
            # raise HTTPException(status_code=400, detail="Unsupported API type")
            return request

        # Get the processed file from ass2-airflow bucket
        processed_file_content = get_file_from_gcp(TXT_BUCKET_NAME, processed_file_name)

        # Prepare the prompt for OpenAI
        prompt = f"""
        Answer the following question based on the information provided in the processed .txt file content:
        Question: {request.question}
        .txt File Content: {processed_file_content}
        Answer:
        """
        
        try:
            openai_response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=500,
                temperature=0.7
        )
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

        
        # Extract the generated answer
        answer = openai_response.choices[0].text.strip()
        return {"openai_response": answer}
    # except Exception as e:
    #     logger.error(f"OpenAI error occurred: {str(e)}")
    #     raise HTTPException(status_code=500, detail="Error with OpenAI API")
    # except Exception as e:
    #     logger.error(f"Unexpected error: {str(e)}")
    #     raise HTTPException(status_code=500, detail="An unexpected error occurred")
    except Exception as e:
        logger.error(f"Error in submit_answer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

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


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
 
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    return email

@app.get("/decode-token")
async def decode_token(token: str = Header(None)):
    if not token:
        raise HTTPException(status_code=400, detail="No token provided")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"decoded_token": payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ... (rest of the code remains the same)

@app.get("/test-jwt")
async def test_jwt(current_user: str = Depends(get_current_user)):
    return {
        "message": "JWT is working correctly",
        "current_user": current_user
    }


@app.post("/register")
def register_user(user: UserRegister):
    connection = load_sql_db_config()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with connection.cursor() as cursor:
            check_user_sql = "SELECT * FROM users WHERE email = %s"
            cursor.execute(check_user_sql, (user.email,))
            existing_user = cursor.fetchone()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
 
            hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
 
            sql = "INSERT INTO users (email, password) VALUES (%s, %s)"
            cursor.execute(sql, (user.email, hashed_password))
        connection.commit()
        return {"message": "User registered successfully"}
 
    except pymysql.Error as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")
 
    finally:
        connection.close()


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    connection = load_sql_db_config()
    if not connection:
        logger.error("Database connection failed")
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email = %s"
            cursor.execute(sql, (form_data.username,))
            user = cursor.fetchone()
            if not user:
                logger.warning(f"Login attempt failed: User not found - {form_data.username}")
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Verify the password
            if not verify_password(form_data.password, user['password']):
                logger.warning(f"Login attempt failed: Incorrect password - {form_data.username}")
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_jwt_token(
                data={"sub": user['email']}, expires_delta=access_token_expires
            )
            logger.info(f"Login successful: {form_data.username}")
            return {"access_token": access_token, "token_type": "bearer"}
    except pymysql.Error as e:
        logger.error(f"Database error during login: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        connection.close()
class QuestionData(BaseModel):
    task_id: str
    question: str
    file_name: str

@app.get("/questions", response_model=List[QuestionData])
async def get_questions(
    current_user: str = Depends(get_current_user),
    file_type: str = Query('all', enum=['all', 'pdf', 'other']), 
    dataset: str = Query('both', enum=['validation', 'test', 'both'])
):
    connection = load_sql_db_config()
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

@app.get("/users/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    return {"email": current_user}

@app.get("/debug-token")
async def debug_token(authorization: str = Header(None)):
    if authorization is None:
        return {"message": "No Authorization header found"}
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return {"message": "Invalid Authorization header format"}
    
    token = parts[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"message": "Token is valid", "payload": payload}
    except jwt.ExpiredSignatureError:
        return {"message": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"message": "Invalid token"}


class ProcessedFileContent(BaseModel):
    processed_content: str

@app.get("/processed_file", response_model=ProcessedFileContent)
async def get_processed_file_content(
    file_name: str = Query(..., description="Name of the file"),
    table: str = Query(..., description="Table name (files_pypdf or files_azure)"),
   # current_user: str = Depends(get_current_user)
):
    connection = load_sql_db_config()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        with connection.cursor() as cursor:
            # Validate table name to prevent SQL injection
            if table not in ['files_pypdf', 'files_azure']:
                raise HTTPException(status_code=400, detail="Invalid table name")
            
            sql = f"SELECT processed_file_name FROM {table} WHERE file_name = %s"
            cursor.execute(sql, (file_name,))
            result = cursor.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="Processed file not found")
            
            processed_file_name = result['processed_file_name']
            
            # Here, you would typically read the content of the processed file
            # For this example, we'll just return the file name
            # In a real scenario, you might read from a file storage system
            processed_content = f"{processed_file_name}"
            
            return {"processed_content": processed_content}
    
    except pymysql.Error as e:
        logger.error(f"Database error while fetching processed file content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        connection.close()