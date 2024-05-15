import os
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageEnhance, ImageFilter, UnidentifiedImageError
import pyttsx3
import base64
from io import BytesIO
import openai
from pydub import AudioSegment
from pydub.playback import play

# Define the model
MODEL = "gpt-4o"  # Using gpt-4o the latest model from OpenAI
openai.api_key = os.environ["OPENAI_API_KEY"]

# Set up the screenshot directory path
screenshot_dir = Path(r"G:\Shadowplay\Baldur's Gate 3")

class ScreenshotHandler(FileSystemEventHandler):
    def on_created(self, event):
        # looks for .png image, waits 1 second so it is written fully to the disc before reading it
        if event.src_path.endswith('.png'):
            print(f"New screenshot detected: {event.src_path}")
            time.sleep(1)  # Delay to ensure the file is fully written
            threading.Thread(target=self.process_image, args=(event.src_path,)).start()

    def process_image(self, image_path):
        print(f"Attempting to process image: {image_path}")
        if not os.path.exists(image_path):
            print(f"Image {image_path} does not exist.")
            return

        try:
            image_base64 = self.resize_and_encode_image(image_path, 126)  # Resize to target size of 126KB
            response = self.get_response(image_base64)
            print(response)
            threading.Thread(target=lambda: self.speak_text(response)).start()

        except Exception as e:
            print(f"Failed to process image {image_path}: {str(e)}")

    def resize_and_encode_image(self, image_path, target_size_kb):
        """ Resize the image to fit within the target size in KB and return base64 string """
        with Image.open(image_path) as img:
            # crop image to were the dialog is
            #width, height = img.size
            #left = int(width * 0.2)
            #upper = int(height * 0.66)
            #right = int(width * 0.7)
            #lower = height
            #img = img.crop((left, upper, right, lower))
            # enhance contrast
            #img = ImageEnhance.Contrast(img)
            #img = img.enhance(2.0)
            # filter smoothness
            #img = img.filter(ImageFilter.SMOOTH)
            # make it grayscale
            #img = img.convert('L')
            # make it black and white to add contrast
            #img = img.point(lambda x: 0 if x < 128 else 255)
            img = img.convert("RGB")  # Ensure image is in RGB mode
            for quality in range(95, 10, -5):
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=quality)
                if buffered.tell() <= target_size_kb * 1024:
                    break
            buffered.seek(0)
            # open image with system default image viewer (for debugging if needed)
            #img.show(title="BG3 Image")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def get_response(self, img):
        """ Send the base64 encoded image to OpenAI and get a response. """
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Analyze this image from Baldur's Gate 3."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Pick a dialog option. Emphesise options that give companion approval, advance romance options, or give character magical items or buffs. Don't explain the pick unless it has immidiate expected value, or next steps that need to be taken. Search BG3 wiki for ideas. Answer shortly."},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpg;base64,{img}"}
                    }
                ]}  
            ],
            temperature=0.0,
        )
        return response.choices[0].message['content']

    def speak_text(self, text):
        """ Use text-to-speech to vocalize the response. """
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"Failed in text-to-speech operation: {str(e)}")

def start_monitoring(path):
    """ Monitor the specified directory for new screenshots and process them. """
    event_handler = ScreenshotHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    print(f"Monitoring {path} for new screenshots...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()

if __name__ == "__main__":
    start_monitoring(screenshot_dir)
