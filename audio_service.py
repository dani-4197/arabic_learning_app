import os
from gtts import gTTS # Google Text-to-Speech library

class AudioService:
    def __init__(self, storage_path='static/audio/'):
        self.storage_path = storage_path
        # Create the directory if it doesn't exist
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def get_pronunciation(self, text):
        """
        Converts Arabic text to speech.
        Uses a hashing-style filename to check for existing cache.
        """
        # Generate a unique filename based on the text
        filename = f"{text.strip()}.mp3"
        file_path = os.path.join(self.storage_path, filename)

        # If file already exists, don't re-download
        if not os.path.exists(file_path):
            try:
                tts = gTTS(text=text, lang='ar')
                tts.save(file_path)
            except Exception as e:
                return None, str(e)

        return filename, None
