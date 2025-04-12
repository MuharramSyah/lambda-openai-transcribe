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
    You are an AI assistant trained to evaluate customer sentiment.

    ### Instructions:
    Read the following conversation between a customer and an agent. Identify the overall customer sentiment as:
    - Positive
    - Neutral
    - Negative
    Also provide a confidence score (0–100%) and a short explanation.
    Please provide answer in Bahasa Indonesia

    ### Response format:
    Sentiment: Positive | Neutral | Negative
    Confidence: [0–100]%
    Explanation: [brief summary]
"""

def lambda_handler(event, context):
    file_path = event['filePath']
    bucket = event['BUCKET_NAME']

    msisdn = get_msisdn(file_path)

    # 2. Read file from done_transcribe
    data = read_file_from_s3(bucket, file_path)

    # 3. Sentiment Analysis + Confidence Score
    result = scoring_satisfaction(data)
    scoring = result['choices'][0]['message']['content'] 

    return {
        'statusCode': 200,
        'body': {
            "msisdn": msisdn,
            "result": scoring,
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


def scoring_satisfaction(text):
    response = requests.post(f"{OPENAI_API_BASE_URL}/chat/completions", 
    headers= {
        "Authorization": "Bearer {}".format(OPENAI_API_KEY),
        "Content-Type": "application/json"
        },
    json={
        "model": OPENAI_API_GPT_MODEL,
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