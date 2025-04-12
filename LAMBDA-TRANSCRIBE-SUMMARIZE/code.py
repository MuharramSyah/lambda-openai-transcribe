import json
import boto3
import os
import re
import requests
import mimetypes
from datetime import datetime

s3 = boto3.client('s3')

OUTPUT_KEY = os.environ.get("OUTPUT_KEY", None)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)
OPENAI_API_GPT_MODEL = os.environ.get("OPENAI_API_GPT_MODEL", None)
OPENAI_API_BASE_URL = "https://api.openai.com/v1"

SYSTEMPROMPT = """
    Ringkas percakapan berikut dengan mencakup empat elemen utama:

    1. **Topik**: Apa inti atau tema utama dari percakapan ini?
    2. **Masalah**: Apa permasalahan atau tantangan yang sedang dibahas?
    3. **Identitas**: Siapa pihak-pihak yang terlibat dalam percakapan ini? (sebutkan peran atau identitas mereka jika tersedia)
    4. **Solusi**: Apa solusi atau kesepakatan yang dicapai selama percakapan?

    Gunakan format bullet point agar ringkas dan mudah dibaca.
"""

def lambda_handler(event, context):
    file_path = event['filePath']
    bucket = event['BUCKET_NAME']

    msisdn = get_msisdn(file_path)

    # 2. Read file from done_transcribe
    data = read_file_from_s3(bucket, file_path)

    # 3. Summarize Conversation
    result = summarize(data)
    summary = result['choices'][0]['message']['content'] 

    return {
        'statusCode': 200,
        'body': {
            "msisdn": msisdn,
            "result": summary,
        }
    }


def get_msisdn(filename):
    """ Get MSISDN Key
    params:
        filename(str): Format s://<bucket-name>/staging/<msisdn>/<filename>
    
    Returns:
        msisdn(str)
    """
    return filename.split('/')[1]

def read_file_from_s3(Bucket, Key):
    response = s3.get_object(Bucket=Bucket, Key=Key)
    body = response['Body'].read().decode('utf-8')
    return body


def summarize(text):
    response = requests.post("https://api.openai.com/v1/chat/completions", 
    headers= {
        "Authorization": "Bearer {}".format(OPENAI_API_KEY),
        "Content-Type": "application/json"
        },
    json={
        "model": "gpt-4o",
        "temperature": 0.5,
        "messages": [
            {
                "role": "system",
                "content": SYSTEMPROMPT
            },
            {
                "role": "user",
                "content": text
            }
        ]
    })
    return response.json()