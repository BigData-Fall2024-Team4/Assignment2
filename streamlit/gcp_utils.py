import os
import pymysql
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

def get_data_from_gcp(file_type='all', dataset='both'):
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
            print(f"Error fetching data from Cloud SQL: {e}")
            return None
    else:
        return None