import os
from gtts import gTTS  # the Google Text-to-Speech library

class AudioService:
    def __init__(self, storage_path='static/audio/'):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def get_pronunciation(self, text):
        # Use the Arabic text itself as the filename so we can check whether the audio file already exists before making a network request to gTTS, this acts as a simple file-based cache - once a word has been fetched once, it never needs to be downloaded again.
        filename  = f"{text.strip()}.mp3"
        file_path = os.path.join(self.storage_path, filename)

        if not os.path.exists(file_path):
            try:
                tts = gTTS(text=text, lang='ar')
                tts.save(file_path)
            except Exception as e:
                return None, str(e)

        return filename, None
