import os
import json
import subprocess
from google.cloud import storage
import mysql.connector
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clone_repository():
    """Clones the GAIA GitHub repository if it doesn't exist."""
    GIT_USERNAME = os.getenv("GIT_USERNAME")
    GIT_TOKEN = os.getenv("GIT_TOKEN")
    GIT_REPO_URL = os.getenv("GIT_REPO_URL")
    LOCAL_CLONE_DIR = "./GAIA"

    git_url_with_credentials = GIT_REPO_URL.replace("https://", f"https://{GIT_USERNAME}:{GIT_TOKEN}@")

    if not os.path.exists(LOCAL_CLONE_DIR):
        try:
            print("Cloning the repository...")
            subprocess.run(["git", "clone", git_url_with_credentials, LOCAL_CLONE_DIR], check=True)
            print(f"Cloned repository into {LOCAL_CLONE_DIR}")
        except subprocess.CalledProcessError as e:
            print(f"Error cloning repository: {e}")
    else:
        print(f"Repository already exists at {LOCAL_CLONE_DIR}")

    return LOCAL_CLONE_DIR

def setup_gcp_clients():
    """Sets up GCP Storage and SQL clients."""
    # Set up credentials
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GCP_SERVICE_ACCOUNT_FILE")
    )

    # Set up Storage client
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.get_bucket(os.getenv("GCP_BUCKET_NAME"))

    # Set up Cloud SQL connection (MySQL)
    connection = mysql.connector.connect(
        user=os.getenv("GCP_SQL_USER"),
        password=os.getenv("GCP_SQL_PASSWORD"),
        host=os.getenv("GCP_SQL_HOST"),
        database=os.getenv("GCP_SQL_DATABASE"),
    )
    cursor = connection.cursor()

    return bucket, connection, cursor

def create_table(cursor, connection):
    """Creates the table for validation cases if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS validation_cases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            task_id VARCHAR(255),
            question TEXT,
            level VARCHAR(50),
            final_answer TEXT,
            file_name VARCHAR(255),
            steps TEXT,
            time_taken VARCHAR(50),
            tools TEXT,
            file_path VARCHAR(500),
            annotator_metadata TEXT
        )
    """)
    connection.commit()

def upload_to_gcs(bucket, local_file_path, file_name):
    """Uploads a file to Google Cloud Storage."""
    try:
        blob = bucket.blob(file_name)
        blob.upload_from_filename(local_file_path)
        print(f"Uploaded {local_file_path} to GCS as {file_name}")
    except Exception as e:
        print(f"Error uploading {local_file_path} to GCS: {e}")

def process_metadata(file_path, cursor, connection, bucket, local_clone_dir):
    """Processes each line in the metadata file, uploads to GCS, and inserts into Cloud SQL."""
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return
    
    with open(file_path, 'r') as file:
        for line in file:
            data = json.loads(line.strip())
            task_id = data.get('task_id', 'NULL')
            question = data.get('Question', 'NULL')
            level = data.get('Level', 'NULL')
            final_answer = data.get('Final answer', 'NULL')
            file_name = data.get('file_name', 'NULL')

            annotator_metadata = data.get('Annotator Metadata', {})
            steps = annotator_metadata.get('Steps', 'NULL')
            time_taken = annotator_metadata.get('How long did this take?', 'NULL')
            tools = annotator_metadata.get('Tools', 'NULL')

            # Upload to GCS if file_name is present
            if file_name and file_name != 'NULL':
                local_file_path = os.path.join(local_clone_dir, '2023', 'validation', file_name)
                if os.path.exists(local_file_path):
                    upload_to_gcs(bucket, local_file_path, file_name)
                else:
                    print(f"File {local_file_path} not found in the GAIA dataset.")
            
            # Insert data into Cloud SQL
            sql = """
            INSERT INTO validation_cases (task_id, question, level, final_answer, file_name, steps, time_taken, tools, file_path, annotator_metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (task_id, question, level, final_answer, file_name, steps, time_taken, tools, local_file_path if file_name else 'NULL', json.dumps(annotator_metadata))
            cursor.execute(sql, values)
            connection.commit()

    print("Data inserted and files uploaded successfully.")

def main():
    local_clone_dir = clone_repository()
    file_path = os.path.join(local_clone_dir, '2023', 'validation', 'metadata.jsonl')
    bucket, connection, cursor = setup_gcp_clients()
    create_table(cursor, connection)

    process_metadata(file_path, cursor, connection, bucket, local_clone_dir)

if __name__ == "__main__":
    main()