from dotenv import load_dotenv
import os
print("GCP Credentials Path:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
# Explicitly specify the path to the .env file
load_dotenv()
print("GCP Credentials Path:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))