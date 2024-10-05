from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from google.cloud import storage
from PyPDF2 import PdfReader
import os
import json
from google.oauth2 import service_account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default arguments for the DAG
default_args = {
    'start_date': days_ago(0),
    'retries': 1,
}

# Define the DAG
dag = DAG(
    dag_id='pdf_preprocessing_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False
)

# Initialize GCP storage client
def setup_gcp_storage():
    credentials_path = os.getenv("GCP_SERVICE_ACCOUNT_FILE")
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    storage_client = storage.Client(credentials=credentials)
    bucket_name = os.getenv("GCP_BUCKET_NAME")
    bucket = storage_client.get_bucket(bucket_name)
    return bucket

# Download PDF from GCP bucket
def download_pdfs_from_gcp(task_id, **kwargs):
    bucket = setup_gcp_storage()
    file_name = kwargs['task_instance'].xcom_pull(task_ids=task_id)
    
    # Create a local directory to store downloaded PDFs
    local_pdf_dir = '/tmp/gaia_pdfs/'
    os.makedirs(local_pdf_dir, exist_ok=True)
    
    # Download the file from GCP
    blob = bucket.blob(file_name)
    local_pdf_path = os.path.join(local_pdf_dir, file_name)
    blob.download_to_filename(local_pdf_path)
    return local_pdf_path

# Extract text and preprocess the PDF file
def preprocess_pdf(**kwargs):
    local_pdf_path = kwargs['task_instance'].xcom_pull(task_ids='download_pdfs_from_gcp')
    output_text = ''
    
    # Extract text from the PDF using PyPDF2
    reader = PdfReader(local_pdf_path)
    
    for page in reader.pages:
        output_text += page.extract_text()  # Extract text from each page

    # Save the processed text to a local file
    processed_text_file = local_pdf_path.replace('.pdf', '_processed.txt')
    with open(processed_text_file, 'w') as f:
        f.write(output_text)
    
    return processed_text_file

# Upload processed file to GCP
def upload_processed_file_to_gcp(**kwargs):
    bucket = setup_gcp_storage()
    processed_text_file = kwargs['task_instance'].xcom_pull(task_ids='preprocess_pdf')
    
    # Upload the processed file to GCP
    processed_file_name = os.path.basename(processed_text_file)
    blob = bucket.blob(f"processed/{processed_file_name}")
    blob.upload_from_filename(processed_text_file)
    
    print(f"Uploaded processed file: {processed_file_name} to GCP.")
    return processed_file_name

# Task 1: Dummy task to provide a file name (In a real case, this will be fetched from metadata)
def provide_pdf_file_name(**kwargs):
    file_name = 'sample_file.pdf'  # Replace this with actual logic to fetch from metadata
    return file_name

# Define the tasks in the DAG
with dag:
    provide_file_name_task = PythonOperator(
        task_id='provide_pdf_file_name',
        python_callable=provide_pdf_file_name
    )
    
    download_pdfs_task = PythonOperator(
        task_id='download_pdfs_from_gcp',
        python_callable=download_pdfs_from_gcp,
        provide_context=True
    )
    
    preprocess_pdf_task = PythonOperator(
        task_id='preprocess_pdf',
        python_callable=preprocess_pdf,
        provide_context=True
    )
    
    upload_processed_file_task = PythonOperator(
        task_id='upload_processed_file_to_gcp',
        python_callable=upload_processed_file_to_gcp,
        provide_context=True
    )
    
    # Task dependencies
    provide_file_name_task >> download_pdfs_task >> preprocess_pdf_task >> upload_processed_file_task
