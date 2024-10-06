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

# Get all PDF file names from test and validation folders
def list_pdf_files_from_gcp(**kwargs):
    bucket = setup_gcp_storage()
    # List files from both test and validation folders
    test_files = [blob.name for blob in bucket.list_blobs(prefix='test/') if blob.name.endswith('.pdf')]
    validation_files = [blob.name for blob in bucket.list_blobs(prefix='validation/') if blob.name.endswith('.pdf')]
    
    # Combine test and validation files
    all_files = test_files + validation_files
    
    # Push the list of files for downstream tasks
    kwargs['task_instance'].xcom_push(key='pdf_files', value=all_files)
    print(f"Found {len(all_files)} PDF files in the bucket.")
    return all_files

# Download PDF from GCP bucket
def download_pdfs_from_gcp(**kwargs):
    bucket = setup_gcp_storage()
    pdf_files = kwargs['task_instance'].xcom_pull(task_ids='list_pdf_files_from_gcp', key='pdf_files')
    
    # Create a local directory to store downloaded PDFs
    local_pdf_dir = '/tmp/gaia_pdfs/'
    os.makedirs(local_pdf_dir, exist_ok=True)
    
    # Download the files from GCP
    local_files = []
    for file_name in pdf_files:
        blob = bucket.blob(file_name)
        local_pdf_path = os.path.join(local_pdf_dir, os.path.basename(file_name))
        blob.download_to_filename(local_pdf_path)
        local_files.append(local_pdf_path)
        print(f"Downloaded {file_name} to {local_pdf_path}")
    
    return local_files

# Extract text and preprocess the PDF file
def preprocess_pdfs(**kwargs):
    local_files = kwargs['task_instance'].xcom_pull(task_ids='download_pdfs_from_gcp')
    processed_files = []
    
    for local_pdf_path in local_files:
        output_text = ''
        reader = PdfReader(local_pdf_path)
        
        for page in reader.pages:
            output_text += page.extract_text()  # Extract text from each page

        # Save the processed text to a local file
        processed_text_file = local_pdf_path.replace('.pdf', '_processed.txt')
        with open(processed_text_file, 'w') as f:
            f.write(output_text)
        
        processed_files.append(processed_text_file)
        print(f"Processed {local_pdf_path}, saved text to {processed_text_file}")
    
    return processed_files

# Upload processed file to GCP
def upload_processed_files_to_gcp(**kwargs):
    bucket = setup_gcp_storage()
    processed_files = kwargs['task_instance'].xcom_pull(task_ids='preprocess_pdfs')
    
    # Upload the processed files to GCP
    for processed_file in processed_files:
        processed_file_name = os.path.basename(processed_file)
        blob = bucket.blob(f"processed/{processed_file_name}")
        blob.upload_from_filename(processed_file)
        print(f"Uploaded processed file: {processed_file_name} to GCP.")
    
    return processed_files

# Define the tasks in the DAG
with dag:
    list_files_task = PythonOperator(
        task_id='list_pdf_files_from_gcp',
        python_callable=list_pdf_files_from_gcp,
        provide_context=True
    )
    
    download_pdfs_task = PythonOperator(
        task_id='download_pdfs_from_gcp',
        python_callable=download_pdfs_from_gcp,
        provide_context=True
    )
    
    preprocess_pdfs_task = PythonOperator(
        task_id='preprocess_pdfs',
        python_callable=preprocess_pdfs,
        provide_context=True
    )
    
    upload_processed_files_task = PythonOperator(
        task_id='upload_processed_files_to_gcp',
        python_callable=upload_processed_files_to_gcp,
        provide_context=True
    )
    
    # Task dependencies
    list_files_task >> download_pdfs_task >> preprocess_pdfs_task >> upload_processed_files_task
