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
OPENAI_API_TRANSCRIBE_MODEL = os.environ.get("OPENAI_API_TRANSCRIBE_MODEL", None)
OPENAI_API_BASE_URL = "https://api.openai.com/v1"


def lambda_handler(event, context):
    file_path = event['filePath']
    bucket = event['BUCKET_NAME']

    msisdn = get_msisdn(file_path)

    response = transcribe_audio(bucket,file_path, 
        prompt="The following Conversation between Customer Service Officer and User. Complain about services")

    improved = improve_transcribe_result(response)

    jsonFile = transform(improved['choices'][0]['message']['content'])

    return {
        'statusCode': 200,
        'body': {
            "msisdn": msisdn,
            "transcription": jsonFile,
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

def read_file_from_s3(bucket_name, key):
    """ 
    """
    response = s3.get_object(Bucket=bucket_name, Key=key)
    file_stream = response['Body']  # This is a streaming object (botocore.response.StreamingBody)
    return file_stream  # Can pass this directly to requests.post(..., files=...)


def transcribe_audio(bucket_name, filename, prompt=""):
    audio_stream = read_file_from_s3(bucket_name, filename)
    mime_type, _ = mimetypes.guess_type(filename)
    response = requests.post(f"{OPENAI_API_BASE_URL}/audio/transcriptions",
                             headers={"Authorization": "Bearer {}".format(OPENAI_API_KEY)},
                             files={"file": (filename, audio_stream, mime_type or "audio/mpeg")},
                             data={"model": OPENAI_API_TRANSCRIBE_MODEL,
                                   "language": "id",
                                   "response_format": "text",
                                   "prompt": prompt})
    return response.text

def improve_transcribe_result(text):
    systemPrompt = """
        Tolong ubah teks hasil transkripsi percakapan berikut menjadi format JSON dengan dua peran utama: "Petugas" dan "User".
    
        Aturan:
        - Identifikasi siapa yang kemungkinan berbicara sebagai Petugas (misalnya memberi informasi, menjawab pertanyaan, memberi instruksi) dan siapa yang kemungkinan adalah User (bertanya, meminta bantuan, atau menerima informasi).
        - Gunakan Bahasa Indonesia yang baik dan benar.
        - Hapus kata pengisi atau pengulangan yang tidak penting (seperti: "eh", "anu", "kayak", dll).
        - Jangan tambahkan informasi yang tidak ada di transkrip.
        - Format akhir harus dalam JSON seperti ini:
    """
    response = requests.post(f"{OPENAI_API_BASE_URL}/chat/completions",
                             headers={
                                "Authorization": "Bearer {}".format(OPENAI_API_KEY),
                                "Content-Type": "application/json"
                            },
                            json={"model": OPENAI_API_GPT_MODEL,
                                  "temperature": 0.5,
                                   "messages": [
                                        {
                                            "role": "system",
                                            "content": systemPrompt
                                        },
                                        {
                                            "role": "user",
                                            "content": text
                                        }
                                        ]})
    return response.json()

def transform(data):
    # Gunakan regex untuk ambil bagian JSON-nya
    match = re.search(r'\[\s*{[\s\S]*?}\s*\]', data)
    parsed = None
    if match:
        json_str = match.group(0)
        try:
            parsed = json.loads(json_str)
            print("JSON berhasil di-parse:")
            return parsed
        except json.JSONDecodeError as e:
            print("Gagal parse JSON:", e)
            return None
    else:
        print("Tidak ditemukan blok JSON dalam teks.")
        return None
    
def store_to_s3(data, msisdn, Bucket, Key):
    timestamp = datetime.now().strftime("%m%d%Y%H%M%S")
    s3_key = f'{Key}/{msisdn}/{timestamp}-transcribe.json'
    json_str = json.dumps(data)
    s3.put_object(
        Bucket=Bucket,
        Key=s3_key,
        Body=json_str,
        ContentType='application/json'
    )
    return s3_key