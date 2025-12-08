import requests
import os
from io import BytesIO
from PIL import Image

class ImageGenerator:
    def __init__(self):
        self.api_url = "https://image.pollinations.ai/prompt/"

    def generate(self, prompt, save_path="generated_image.png"):
        url = self.api_url + requests.utils.quote(prompt)
        print("[ImageGen] Requesting:", url)

        resp = requests.get(url)

        if resp.status_code != 200:
            raise Exception(f"Pollinations API error: {resp.status_code}")

        img = Image.open(BytesIO(resp.content))
        
        filename = "".join(c for c in prompt if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = filename[:50]  
        save_path = os.path.join(os.path.dirname(save_path), f"{filename}.png")
        
        img.save(save_path)
        return save_path
