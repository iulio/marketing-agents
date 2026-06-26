# app/image_gen.py
"""
Image Generation Module - Supports Local, HuggingFace, and Replicate APIs
"""
import os
import base64
from io import BytesIO
from typing import Optional, Dict
import requests
from PIL import Image

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "huggingface")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_MODEL = "runwayml/stable-diffusion-v1-5"

class ImageGenerator:
    def __init__(self, provider: str = None):
        self.provider = provider or IMAGE_PROVIDER
        self._init_provider()
    
    def _init_provider(self):
        if self.provider == "local":
            self._init_local()
        elif self.provider == "replicate":
            self._init_replicate()
        else:
            self.provider = "huggingface"
            self._init_huggingface()
    
    def _init_local(self):
        self.pipe = None
        print("[ImageGen] Local mode (requires diffusers)")
    
    def _init_huggingface(self):
        self.api_url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
        self.headers = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}
        print("[ImageGen] HuggingFace API initialized")
    
    def _init_replicate(self):
        self.replicate_client = None
        print("[ImageGen] Replicate mode (requires replicate library)")
    
    def generate(self, prompt: str, negative_prompt: str = "", width: int = 512, height: int = 512) -> Optional[str]:
        if self.provider == "huggingface":
            return self._generate_huggingface(prompt, negative_prompt, width, height)
        return None
    
    def _generate_huggingface(self, prompt, negative_prompt, width, height):
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": 30,
                }
            }
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            if response.status_code == 200:
                img_data = base64.b64encode(response.content).decode()
                return f"data:image/png;base64,{img_data}"
            return None
        except Exception as e:
            print(f"[ImageGen] HF API error: {e}")
            return None

def generate_campaign_images(prompt: str, num_images: int = 2) -> list:
    generator = ImageGenerator()
    images = []
    for i in range(num_images):
        img = generator.generate(prompt)
        if img:
            images.append(img)
    return images