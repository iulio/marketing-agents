# app/image_gen.py
"""
Image Generation Module - Supports Local, HuggingFace, and Replicate APIs
"""
import os
import base64
import time
from io import BytesIO
from typing import Optional, Dict, List
import requests
from PIL import Image

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "huggingface")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_MODEL = "runwayml/stable-diffusion-v1-5"
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

class ImageGenerator:
    def __init__(self, provider: str = None):
        self.provider = provider or IMAGE_PROVIDER
        self.max_retries = 3
        self.retry_delay = 2
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
        if not HF_API_TOKEN:
            print("[ImageGen] ⚠️  HF_API_TOKEN not set - image generation will fail")
        else:
            print("[ImageGen] ✅ HuggingFace API initialized")
    
    def _init_replicate(self):
        self.replicate_client = None
        if REPLICATE_API_TOKEN:
            try:
                import replicate
                self.replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)
                print("[ImageGen] ✅ Replicate API initialized")
            except ImportError:
                print("[ImageGen] ⚠️  Replicate library not installed")
        else:
            print("[ImageGen] ⚠️  REPLICATE_API_TOKEN not set")
    
    def generate(self, prompt: str, negative_prompt: str = "", width: int = 512, height: int = 512) -> Optional[str]:
        """Generate an image from text prompt with retries."""
        if self.provider == "huggingface":
            return self._generate_huggingface(prompt, negative_prompt, width, height)
        elif self.provider == "replicate" and self.replicate_client:
            return self._generate_replicate(prompt, negative_prompt, width, height)
        return None
    
    def _generate_huggingface(self, prompt, negative_prompt, width, height):
        """Generate using HuggingFace Inference API with retry logic."""
        if not HF_API_TOKEN:
            print("[ImageGen] ❌ HF_API_TOKEN not configured")
            return None
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": negative_prompt or "low quality, blurry, distorted",
                "width": width,
                "height": height,
                "num_inference_steps": 25,
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    img_data = base64.b64encode(response.content).decode()
                    return f"data:image/png;base64,{img_data}"
                elif response.status_code == 503:
                    print(f"[ImageGen] Model loading (attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"[ImageGen] API error {response.status_code}: {response.text[:200]}")
                    return None
                    
            except requests.Timeout:
                print(f"[ImageGen] Timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                print(f"[ImageGen] HuggingFace error: {e}")
                return None
        
        return None
    
    def _generate_replicate(self, prompt, negative_prompt, width, height):
        """Generate using Replicate API."""
        try:
            output = self.replicate_client.run(
                "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c47161d6b2c2d2e",
                input={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt or "low quality, blurry",
                    "width": width,
                    "height": height,
                    "num_inference_steps": 25
                }
            )
            if output and len(output) > 0:
                return output[0]
            return None
        except Exception as e:
            print(f"[ImageGen] Replicate error: {e}")
            return None


def generate_campaign_images(prompt: str, industry: str = "general", num_images: int = 2) -> List[str]:
    """
    Generate multiple images for a marketing campaign.
    
    Args:
        prompt: Base marketing prompt
        industry: Industry type for template-based styling
        num_images: Number of variations to generate
    
    Returns:
        List of base64-encoded images (or empty list if generation fails)
    """
    try:
        from .industry_prompts import get_industry_template
        template = get_industry_template(industry)
        visual_style = template.get("visual_style", "High-quality professional imagery")
    except:
        visual_style = "High-quality professional marketing imagery"
    
    generator = ImageGenerator()
    images = []
    
    for i in range(num_images):
        variation = f"{prompt} Style: {visual_style}. Variation {i+1}. Professional marketing asset."
        print(f"[ImageGen] Generating image {i+1}/{num_images}: {variation[:60]}...")
        
        img = generator.generate(variation)
        if img:
            images.append(img)
            print(f"[ImageGen] ✅ Image {i+1} generated successfully")
        else:
            print(f"[ImageGen] ❌ Failed to generate image {i+1}")
    
    return images
