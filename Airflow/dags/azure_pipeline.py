import os
import json
import shutil
import subprocess
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from google.cloud import storage
from env_var import AZURE_ENDPOINT, AZURE_KEY, GCP_BUCKET_NAME, GCP_SERVICE_ACCOUNT_FILE, GIT_USERNAME, GIT_TOKEN, GIT_REPO_URL

# Default arguments for the DAG
default_args = {
    'start_date': days_ago(0),
    'retries': 1,
}

# Define the DAG
dag = DAG(
    dag_id='azure_pdf_processing_dag',
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
                        # Add the dataset type and file path for later reference
                        data['dataset'] = dataset
                        data['file_path'] = os.path.join(local_clone_dir, '2023', dataset, data['file_name'])
                        pdf_files.append(data)
                        count += 1
        else:
            print(f"Metadata file not found for {dataset}")

        dataset_counts[dataset] = count
    
    # Print the count of PDFs in each dataset
    for dataset, count in dataset_counts.items():
        print(f"Found {count} PDF files in {dataset} dataset.")

    return pdf_files

# Step 3: Process each PDF with Azure AI Document Intelligence
def process_pdf_with_azure(pdf_file, **kwargs):
    pdf_path = pdf_file['file_path']
    dataset = pdf_file['dataset']  # Extract dataset information
    output_txt_path = pdf_path.replace('.pdf', f'_{dataset}_azure.txt')

    # Initialize the Document Analysis client
    document_analysis_client = DocumentAnalysisClient(
        endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY)
    )

    # Read the PDF file
    with open(pdf_path, "rb") as f:
        poller = document_analysis_client.begin_analyze_document("prebuilt-document", document=f)
    result = poller.result()

    # Extract and write the content
    with open(output_txt_path, "w", encoding="utf-8") as f:
        for page in result.pages:
            for line in page.lines:
                f.write(f"{line.content}\n")

        for table in result.tables:
            f.write(f"\n--- Table ---\n")
            for cell in table.cells:
                f.write(f"{cell.content}\t")
            f.write("\n")

    print(f"Processed {pdf_path} with Azure AI Document Intelligence")
    return {
        'file_path': output_txt_path,
        'dataset': dataset
    }

def process_all_pdfs(**kwargs):
    pdf_files = kwargs['ti'].xcom_pull(task_ids='filter_pdfs')
    processed_files = []
    failed_files = []
    
    for pdf_file in pdf_files:
        try:
            txt_file_metadata = process_pdf_with_azure(pdf_file)
            processed_files.append(txt_file_metadata)
        except Exception as e:
            print(f"Error processing {pdf_file['file_name']}: {str(e)}")
            failed_files.append(pdf_file['file_name'])
    
    print(f"Processing complete. Processed: {len(processed_files)}, Failed: {len(failed_files)}")
    
    kwargs['ti'].xcom_push(key='processed_files', value=processed_files)
    kwargs['ti'].xcom_push(key='failed_files', value=failed_files)

# Step 4: Upload the .txt files to GCP, storing them in 'test' or 'validation' folders based on the dataset
def upload_to_gcp(txt_file_path, dataset, **kwargs):
    try:
        storage_client = storage.Client.from_service_account_json(GCP_SERVICE_ACCOUNT_FILE)
        bucket = storage_client.bucket(GCP_BUCKET_NAME)
        
        # Add the dataset folder (test or validation) to the blob name
        destination_blob_name = f"{dataset}/{os.path.basename(txt_file_path)}"
        
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(txt_file_path)
        print(f"{txt_file_path} uploaded to {GCP_BUCKET_NAME}/{dataset}.")
        return True
    except Exception as e:
        print(f"Error uploading to GCP: {txt_file_path}")
        print(f"Error details: {str(e)}")
        return False

def upload_all_files(**kwargs):
    processed_files = kwargs['ti'].xcom_pull(task_ids='process_pdfs', key='processed_files')
    uploaded_count = 0
    failed_count = 0
    
    for txt_file_metadata in processed_files:
        # Extract the dataset (test or validation) from the file metadata
        dataset = txt_file_metadata['dataset']
        txt_file_path = txt_file_metadata['file_path']
        
        if upload_to_gcp(txt_file_path, dataset):
            uploaded_count += 1
        else:
            failed_count += 1
    
    print(f"Upload complete. Uploaded: {uploaded_count}, Failed: {failed_count}")

# Define tasks in the DAG
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

    # Process all PDF files using Azure
    process_pdfs = PythonOperator(
        task_id='process_pdfs',
        python_callable=process_all_pdfs,
        provide_context=True
    )

    # Upload all processed files
    upload_files = PythonOperator(
        task_id='upload_files',
        python_callable=upload_all_files,
        provide_context=True
    )

    # Task flow
    clone_repo >> filter_pdfs >> process_pdfs >> upload_files