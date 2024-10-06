import os
import json
import subprocess
import shutil
from airflow import DAG
from airflow.operators.python import PythonOperator
from google.cloud import storage
from PyPDF2 import PdfReader
from datetime import datetime
from airflow.utils.dates import days_ago
from env_var import GIT_USERNAME, GIT_TOKEN, GIT_REPO_URL, GCP_BUCKET_NAME, GCP_SERVICE_ACCOUNT_FILE

# Default arguments for the DAG
default_args = {
    'start_date': days_ago(0),
    'retries': 1,
}

# Define the DAG
dag = DAG(
    dag_id='gaia_pdf_processing_dag',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False
)

# Step 1: Clone the dataset from Hugging Face including LFS files
def clone_repository(**kwargs):
    LOCAL_CLONE_DIR = "./GAIA"

    git_url_with_credentials = GIT_REPO_URL.replace("https://", f"https://{GIT_USERNAME}:{GIT_TOKEN}@")

    # Check if the repository directory exists
    if os.path.exists(LOCAL_CLONE_DIR):
        try:
            # Delete the existing directory
            print(f"Directory {LOCAL_CLONE_DIR} exists. Deleting it...")
            shutil.rmtree(LOCAL_CLONE_DIR)
        except Exception as e:
            print(f"Error deleting directory {LOCAL_CLONE_DIR}: {e}")
            return None

    # Now proceed to clone the repository again
    try:
        # Clone the repository
        print("Cloning the repository with Git LFS support...")
        subprocess.run(["git", "clone", git_url_with_credentials, LOCAL_CLONE_DIR], check=True)
        
        # Change the working directory to the cloned repo
        os.chdir(LOCAL_CLONE_DIR)

        # Initialize Git LFS in case it's not initialized
        subprocess.run(["git", "lfs", "install"], check=True)

        # Pull the LFS files after cloning the repository
        subprocess.run(["git", "lfs", "pull"], check=True)

        print(f"Successfully cloned repository into {LOCAL_CLONE_DIR} and downloaded all LFS files.")
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository or downloading LFS files: {e}")
        return None

    return LOCAL_CLONE_DIR

# Step 2: Filter only the PDF files from both validation and test metadata.jsonl
def filter_pdf_files(**kwargs):
    local_clone_dir = kwargs['ti'].xcom_pull(task_ids='clone_repo')
    datasets = ['validation', 'test']
    pdf_files = []
    dataset_counts = {}

    for dataset in datasets:
        metadata_file = os.path.join(local_clone_dir, '2023', dataset, 'metadata.jsonl')
        count = 0
        
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get('file_name', '').endswith('.pdf'):
                        # Add the dataset type for later reference
                        data['dataset'] = dataset
                        pdf_files.append(data)
                        count += 1
        else:
            print(f"Metadata file not found for {dataset}")

        dataset_counts[dataset] = count
    
    # Print the count of PDFs in each dataset
    for dataset, count in dataset_counts.items():
        print(f"Found {count} PDF files in {dataset} dataset.")

    return pdf_files

# Step 3: Process each PDF (extract text, images, tables)
def process_pdf(pdf_file, **kwargs):
    dataset = pdf_file['dataset']
    pdf_path = os.path.join(f"./GAIA/2023/{dataset}/", pdf_file['file_name'])
    
    print(f"Processing PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return None

    # Get the size of the PDF file
    pdf_size = os.path.getsize(pdf_path)
    
    output_txt_path = pdf_path.replace('.pdf', '.txt')
    
    try:
        # Simple text extraction using PyPDF
        with open(pdf_path, 'rb') as pdf_file_obj:
            reader = PdfReader(pdf_file_obj)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
        
        # Write text to a file
        with open(output_txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        
        print(f"Successfully processed: {pdf_path}")
        return output_txt_path
    except Exception as e:
        print(f"Error processing PDF: {pdf_path}")
        print(f"Error details: {str(e)}")
        print(f"PDF file size: {pdf_size} bytes")
        return None
    
# Step 4: Upload the .txt files to GCP
def upload_to_gcp(txt_file_path, **kwargs):
    try:
        storage_client = storage.Client.from_service_account_json(GCP_SERVICE_ACCOUNT_FILE)
        bucket = storage_client.bucket(GCP_BUCKET_NAME)
        destination_blob_name = os.path.basename(txt_file_path)

        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(txt_file_path)
        print(f"{txt_file_path} uploaded to {GCP_BUCKET_NAME}.")
        return True
    except Exception as e:
        print(f"Error uploading to GCP: {txt_file_path}")
        print(f"Error details: {str(e)}")
        return False

# Step 5: Define tasks in the DAG
with dag:
    # Clone the dataset
    clone_repo = PythonOperator(
        task_id='clone_repo',
        python_callable=clone_repository
    )

    # Filter only the PDFs from both validation and test datasets
    filter_pdfs = PythonOperator(
        task_id='filter_pdfs',
        python_callable=filter_pdf_files,
        provide_context=True
    )

    # Process each PDF file (extract text and save as .txt)
    def process_and_upload_pdfs(**kwargs):
        pdf_files = kwargs['ti'].xcom_pull(task_ids='filter_pdfs')
        processed_count = 0
        failed_count = 0
        
        for pdf_file in pdf_files:
            txt_file_path = process_pdf(pdf_file)
            if txt_file_path:
                if upload_to_gcp(txt_file_path):
                    processed_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1
        
        print(f"Processing complete. Processed: {processed_count}, Failed: {failed_count}")

    process_pdfs = PythonOperator(
        task_id='process_pdfs',
        python_callable=process_and_upload_pdfs,
        provide_context=True
    )

    # Task flow
    clone_repo >> filter_pdfs >> process_pdfs
