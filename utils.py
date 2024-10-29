import fitz  # PyMuPDF for PDF text extraction
import boto3
import os

def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text

def upload_to_s3(file_path, bucket_name, s3_client):
    file_name = os.path.basename(file_path)
    s3_client.upload_file(file_path, bucket_name, file_name)
    return f"s3://{bucket_name}/{file_name}"
