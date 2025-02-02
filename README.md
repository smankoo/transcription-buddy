# AWS Transcribe Meeting Transcription Tool

## Overview

This Python-based tool allows users to transcribe audio files using AWS Transcribe. It uploads an audio file to an S3 bucket, starts a transcription job, and fetches the transcribed text for further processing. The tool is designed to handle speaker identification and structured summarization.

## Features

- Upload audio files to AWS S3
- Start a transcription job with AWS Transcribe
- Monitor job status and retrieve transcripts
- Process and clean transcripts for structured output
- Generate meeting summaries and action items
- Provide a web-based UI using Streamlit

## Installation

### Prerequisites

- Python 3.8+
- AWS CLI configured with appropriate credentials
- An S3 bucket for storing audio and transcript files
- `pip` package manager

### Setup

1. Clone this repository:
   ```sh
   git clone https://github.com/smankoo/aws-transcribe-tool.git
   cd aws-transcribe-tool
   ```
2. Create a virtual environment and activate it:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   Copy `.env.example` to `.env` and update it with your S3 bucket details:
   ```sh
   cp .env.example .env
   ```
   Update `.env` with:
   ```sh
   S3_BUCKET=your-s3-bucket-name
   AUDIO_FILE_PATH=".audio/filename"
   OUTPUT_DIR="./output"
   ```

## Usage

### CLI Usage

Run the transcription process with:

```sh
python main.py
```

### Web UI

Start the Streamlit UI:

```sh
streamlit run app.py
```

Upload an audio file through the UI and monitor transcription progress.

## File Structure

```
├── app.py                      # Streamlit web interface
├── main.py                     # CLI-based transcription workflow
├── process_transcribe_output.py # Post-processing of AWS transcripts
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment variables
├── .gitignore                   # Ignore unnecessary files
├── README.md                    # This documentation
```

## How It Works

1. **Upload Audio**: The audio file is uploaded to S3.
2. **Start Transcription**: AWS Transcribe processes the audio.
3. **Monitor Status**: The script polls the job until completion.
4. **Download & Process**: The transcript is downloaded and formatted.
5. **Summarize & Extract**: The cleaned transcript is structured into a readable format.

## Contributing

Contributions are welcome! Please fork the repo, make changes, and submit a pull request.

## License

This project is licensed under the MIT License.

## Contact

For support or questions, open an issue on GitHub or contact `your-email@example.com`.
