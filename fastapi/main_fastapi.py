from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
import pymysql
import os
from dotenv import load_dotenv

load_dotenv('.env')

app = FastAPI()

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

class User(BaseModel):
    name: str
    email: str
    password: str

class UserHistory(BaseModel):
    user_email: str
    user_question: str
    user_attempt_answer_1: str
    user_attempt_answer_2: str
    question_level: str

@app.post("/register")
def register_user(user: User):
    connection = load_sql_db_config()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user.name, user.email, user.password))
        connection.commit()
        return {"message": "User registered successfully"}
    except pymysql.Error as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")
    finally:
        connection.close()

@app.post("/login")
def login_user(user: User):
    connection = load_sql_db_config()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email = %s AND password = %s"
            cursor.execute(sql, (user.email, user.password))
            result = cursor.fetchone()
            if result:
                return {"message": "Login successful"}
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
    finally:
        connection.close()

@app.post("/user-history")
def add_user_history(history: UserHistory):
    connection = load_sql_db_config()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO user_history 
            (user_question, user_attempt_answer_1, user_attempt_answer_2, question_level) 
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                history.user_question,
                history.user_attempt_answer_1,
                history.user_attempt_answer_2,
                history.question_level
            ))
        connection.commit()
        return {"message": "User history added successfully"}
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