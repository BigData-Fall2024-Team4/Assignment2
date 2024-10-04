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

def get_data_from_gcp():
    """Retrieves question data from the GCP Cloud SQL database."""
    connection = get_gcp_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT task_id, question FROM validation_cases")
                data = cursor.fetchall()
            connection.close()
            return data
        except pymysql.Error as e:
            print(f"Error fetching data from Cloud SQL: {e}")
            return None
    else:
        return None