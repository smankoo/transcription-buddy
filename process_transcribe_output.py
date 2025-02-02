import json
from dotenv import load_dotenv
import os

load_dotenv()
OUTPUT_DIR = os.getenv("OUTPUT_DIR")


def process_output_file(transcript_filename, audio_filename):
    file_base_name = os.path.basename(audio_filename)
    with open(transcript_filename, "r") as f:
        data = json.load(f)

        # combine all speech by a speaker in one turn. Only print new speaker label when the speaker changes
        current_speaker = None
        current_transcript = ""

        processed_transcript = ""

        for audio_segment in data["results"]["audio_segments"]:
            speaker = audio_segment["speaker_label"]
            transcript = audio_segment["transcript"]

            if speaker != current_speaker:
                if current_transcript:
                    processed_transcript += (
                        current_speaker + ": " + current_transcript + "\n"
                    )
                current_speaker = speaker
                current_transcript = transcript
            else:
                current_transcript += " " + transcript

        if current_transcript:
            processed_transcript += current_speaker + ": " + current_transcript + "\n"

    with open(f"{OUTPUT_DIR}/{file_base_name}_processed_transcript.txt", "w") as f:
        f.write(processed_transcript)

    print("Processed transcript output is now available in: processed_transcript.txt")
