import google.generativeai as genai
import os
import time

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

def transcribe_audio(file_path):
    """
    Transcribes audio file using Gemini 1.5 Flash.
    """
    if not GOOGLE_API_KEY:
        return "Gemini API key not configured."

    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        
        # Upload the file
        audio_file = genai.upload_file(path=file_path)
        
        # Wait for file to be processed
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)

        if audio_file.state.name == "FAILED":
            raise Exception("Audio file processing failed.")

        # Transcribe
        response = model.generate_content([
            "Transcribe this audio file into text. Return ONLY the transcription, no other text.",
            audio_file
        ])
        
        # Clean up the file from Gemini cloud
        genai.delete_file(audio_file.name)
        
        return response.text.strip()
    except Exception as e:
        print(f"Transcription Error: {e}")
        return None
