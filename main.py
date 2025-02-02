import boto3
import time
import json
import logging
import sys
from dotenv import load_dotenv
import os

from process_transcribe_output import process_output_file


load_dotenv()

# get from env
S3_BUCKET = os.getenv("S3_BUCKET")
AUDIO_FILE_PATH = os.getenv("AUDIO_FILE_PATH")
OUTPUT_DIR = os.getenv("OUTPUT_DIR")

# create OUTPUT_DIR if not exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def upload_file_to_s3(local_file_path, s3_bucket, s3_key):
    """Uploads a local file to S3."""
    s3 = boto3.client("s3")
    try:
        s3.upload_file(local_file_path, s3_bucket, s3_key)
        logging.info(
            f"Successfully uploaded {local_file_path} to s3://{s3_bucket}/{s3_key}"
        )
    except Exception as e:
        logging.error(f"Error uploading file to S3: {e}")
        sys.exit(1)


def start_transcription_job(
    job_name,
    s3_bucket,
    s3_key,
    language_code="en-US",
    enable_speaker_labels=True,
    max_speaker_labels=10,
):
    """Starts an AWS Transcribe job using the S3 URI."""
    transcribe = boto3.client("transcribe")
    media_uri = f"s3://{s3_bucket}/{s3_key}"
    media_format = s3_key.split(".")[-1]  # Assuming file extension indicates format

    # Prepare parameters for the transcription job
    params = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": media_uri},
        "MediaFormat": media_format,
        "LanguageCode": language_code,
        "OutputBucketName": s3_bucket,
    }

    if enable_speaker_labels:
        # Move speaker labels parameters inside the Settings dictionary
        params["Settings"] = {
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": max_speaker_labels,
        }

    try:
        response = transcribe.start_transcription_job(**params)
        logging.info(f'Transcription job "{job_name}" started successfully.')
        return response
    except Exception as e:
        logging.error(f"Error starting transcription job: {e}")
        sys.exit(1)


def poll_transcription_job(job_name, interval=30, timeout=1800):
    """Polls the transcription job until completion or timeout."""
    transcribe = boto3.client("transcribe")
    start_time = time.time()
    while True:
        try:
            result = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            status = result["TranscriptionJob"]["TranscriptionJobStatus"]
            logging.info(f"Job status: {status}")
            if status in ["COMPLETED", "FAILED"]:
                return result
            if time.time() - start_time > timeout:
                logging.error("Polling timed out.")
                return None
            time.sleep(interval)
        except Exception as e:
            logging.error(f"Error polling job status: {e}")
            time.sleep(interval)


def download_transcript_from_s3(s3_bucket, job_name, local_file):
    """Downloads the transcript file from S3 using boto3."""
    s3 = boto3.client("s3")
    transcript_key = (
        f"{job_name}.json"  # AWS Transcribe names the output file as <job_name>.json
    )
    try:
        s3.download_file(s3_bucket, transcript_key, local_file)
        logging.info(f"Transcript downloaded successfully to {local_file}.")
        with open(local_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error downloading transcript from S3: {e}")
        return None


def main():
    # Configuration: Replace these with inputs or command line arguments as needed
    ts = int(time.time())

    s3_key = f"transcribe-inputs/{ts}.{AUDIO_FILE_PATH.split('/')[-1]}"

    job_name = f"transcription-job-{ts}"  # Unique job name per transcription
    language_code = "en-US"

    logging.info(f"Starting transcription job: {job_name}")

    # Step 1: Upload the local file to S3
    upload_file_to_s3(AUDIO_FILE_PATH, S3_BUCKET, s3_key)

    # Step 2: Start the transcription job with speaker identification enabled
    start_transcription_job(
        job_name,
        S3_BUCKET,
        s3_key,
        language_code,
        enable_speaker_labels=True,
        max_speaker_labels=10,
    )

    # Step 3: Poll for job completion
    result = poll_transcription_job(job_name)
    if result and result["TranscriptionJob"]["TranscriptionJobStatus"] == "COMPLETED":
        # Step 4: Download transcript from S3
        transcript_file = f"{OUTPUT_DIR}/{job_name}.json"
        transcript = download_transcript_from_s3(S3_BUCKET, job_name, transcript_file)
        if transcript:
            logging.info(
                f"Transcript successfully downloaded and saved as {transcript_file}."
            )
            process_output_file(transcript_file, AUDIO_FILE_PATH)

        else:
            logging.error("Failed to download transcript from S3.")
    else:
        logging.error("Transcription job did not complete successfully.")


if __name__ == "__main__":
    main()
