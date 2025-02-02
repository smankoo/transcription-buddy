import streamlit as st
import boto3
import time
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
S3_BUCKET = os.getenv("S3_BUCKET")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

st.set_page_config(page_title="Audio Transcription App", layout="wide")
st.title("Audio Transcription App")
st.markdown(
    """
    Upload an audio file below and let our service transcribe it using AWS Transcribe.
    
    **Note:** Transcription might take several minutes. Please be patient while the job is processed.
    """
)

# ---------- Helper Functions ----------


def upload_file_to_s3(local_file_path, s3_bucket, s3_key):
    """Uploads a local file to S3."""
    s3 = boto3.client("s3")
    try:
        s3.upload_file(local_file_path, s3_bucket, s3_key)
        st.success(f"Successfully uploaded file to s3://{s3_bucket}/{s3_key}")
        return True
    except Exception as e:
        st.error(f"Error uploading file to S3: {e}")
        return False


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
    media_format = s3_key.split(".")[-1]  # assuming file extension indicates format

    params = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": media_uri},
        "MediaFormat": media_format,
        "LanguageCode": language_code,
        "OutputBucketName": s3_bucket,
    }
    if enable_speaker_labels:
        params["Settings"] = {
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": max_speaker_labels,
        }
    try:
        response = transcribe.start_transcription_job(**params)
        st.info(f'Transcription job "{job_name}" started successfully.')
        return response
    except Exception as e:
        st.error(f"Error starting transcription job: {e}")
        return None


def get_circle_html(percentage):
    """
    Returns HTML for a circular progress indicator.
    The circle is full (100%) when percentage is 100 and gradually empties as the value decreases.
    """
    circumference = 2 * 3.1416 * 20  # r = 20
    dash_offset = (1 - percentage / 100) * circumference
    return f"""
    <div style="position: relative; width: 50px; height: 50px;">
      <svg width="50" height="50">
        <circle cx="25" cy="25" r="20" stroke="#eee" stroke-width="5" fill="none" />
        <circle cx="25" cy="25" r="20" stroke="#007bff" stroke-width="5" fill="none"
          stroke-dasharray="{circumference}"
          stroke-dashoffset="{dash_offset}"
          transform="rotate(-90 25 25)" />
      </svg>
      <div style="position:absolute; top:0; left:0; width:50px; height:50px; display:flex; align-items:center; justify-content:center;">
        <span style="font-size:12px;">{int(percentage)}%</span>
      </div>
    </div>
    """


def poll_transcription_job(job_name, interval=30, timeout=1800):
    """
    Polls the transcription job until completion or timeout.
    (This may take several minutes – please be patient.)
    Displays a progress circle that resets after each check.
    """
    transcribe = boto3.client("transcribe")
    start_time = time.time()
    status_placeholder = st.empty()
    last_checked_placeholder = st.empty()
    circle_placeholder = st.empty()  # New placeholder for the progress circle
    while True:
        try:
            result = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            status = result["TranscriptionJob"]["TranscriptionJobStatus"]
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            status_placeholder.info(f"Job status: {status}")
            last_checked_placeholder.info(f"Last checked: {current_time}")
            # Immediately after the check, reset the circle to full (100%)
            circle_placeholder.markdown(get_circle_html(100), unsafe_allow_html=True)
            if status in ["COMPLETED", "FAILED"]:
                return result
            # Instead of a single sleep, update the circle progress every second
            for i in range(interval):
                percentage = 100 * (1 - (i / interval))
                circle_placeholder.markdown(
                    get_circle_html(percentage), unsafe_allow_html=True
                )
                time.sleep(1)
            if time.time() - start_time > timeout:
                st.error("Polling timed out.")
                return None
        except Exception as e:
            st.error(f"Error polling job status: {e}")
            time.sleep(interval)


def download_transcript_from_s3(s3_bucket, job_name, local_file):
    """Downloads the transcript file from S3."""
    s3 = boto3.client("s3")
    transcript_key = f"{job_name}.json"  # AWS Transcribe outputs <job_name>.json
    try:
        s3.download_file(s3_bucket, transcript_key, local_file)
        st.success(f"Transcript downloaded successfully to {local_file}.")
        with open(local_file, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error downloading transcript from S3: {e}")
        return None


def process_transcript_file(transcript_file):
    """
    Process the raw transcript JSON into a cleaned transcript.

    This function expects the transcript JSON to contain a list of audio segments
    with a 'speaker_label' and 'transcript' in data["results"]["audio_segments"].
    Adjust as needed for your actual AWS Transcribe output.
    """
    try:
        with open(transcript_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Error reading transcript file: {e}")
        return ""

    current_speaker = None
    current_transcript = ""
    processed_transcript = ""
    # Loop over audio segments (this structure may need adjustment per your output)
    for segment in data.get("results", {}).get("audio_segments", []):
        speaker = segment.get("speaker_label", "Unknown")
        transcript = segment.get("transcript", "")
        if speaker != current_speaker:
            if current_transcript:
                processed_transcript += f"{current_speaker}: {current_transcript}\n"
            current_speaker = speaker
            current_transcript = transcript
        else:
            current_transcript += " " + transcript
    if current_transcript:
        processed_transcript += f"{current_speaker}: {current_transcript}\n"
    return processed_transcript


# ---------- Streamlit UI Workflow ----------

# File uploader for audio file
uploaded_file = st.file_uploader(
    "Choose an audio file", type=["mp3", "wav", "m4a", "flac"]
)

# Let the user specify the maximum number of speakers (default 10)
max_speakers = st.number_input(
    "Maximum number of speakers", min_value=1, max_value=20, value=10, step=1
)

if uploaded_file is not None:
    st.audio(uploaded_file, format="audio/wav")
    # Save the uploaded file temporarily.
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    temp_file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button("Transcribe Audio"):
        ts = int(time.time())
        # Construct a unique S3 key and job name
        s3_key = f"transcribe-inputs/{ts}_{uploaded_file.name}"
        job_name = f"transcription-job-{ts}"
        language_code = "en-US"

        st.info("Uploading file to S3...")
        if upload_file_to_s3(temp_file_path, S3_BUCKET, s3_key):
            st.info("Starting transcription job...")
            if start_transcription_job(
                job_name,
                S3_BUCKET,
                s3_key,
                language_code,
                max_speaker_labels=max_speakers,
            ):
                with st.spinner("Transcribing... This might take several minutes."):
                    result = poll_transcription_job(job_name, interval=30, timeout=1800)
                if (
                    result
                    and result["TranscriptionJob"]["TranscriptionJobStatus"]
                    == "COMPLETED"
                ):
                    transcript_file = os.path.join(OUTPUT_DIR, f"{job_name}.json")
                    transcript_json = download_transcript_from_s3(
                        S3_BUCKET, job_name, transcript_file
                    )
                    if transcript_json:
                        st.success("Transcription job completed!")
                        processed_transcript = process_transcript_file(transcript_file)
                        if processed_transcript:
                            st.subheader("Processed Transcript")
                            st.text_area("Transcript", processed_transcript, height=300)
                            # Provide a download button for the transcript file.
                            st.download_button(
                                label="Download Transcript",
                                data=processed_transcript,
                                file_name=f"{job_name}_processed_transcript.txt",
                                mime="text/plain",
                            )
                        else:
                            st.error("Could not process the transcript.")
                    else:
                        st.error("Failed to download transcript.")
                else:
                    st.error("Transcription job did not complete successfully.")
        else:
            st.error("File upload failed.")
