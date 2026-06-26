"""
Image Generation Module
Supports: Local Stable Diffusion, HuggingFace Inference API, Replicate API
"""
import os
import base64
from io import BytesIO
from typing import Optional, Dict, Any
import requests
from PIL import Image

# ================================================================
# CONFIGURATION
# ================================================================
# Set your preferred provider: "local", "huggingface", "replicate"
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "huggingface")

# HuggingFace Inference API (free tier)
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")  # Get from huggingface.co/settings/tokens
HF_MODEL = "runwayml/stable-diffusion-v1-5"  # Free models: "stabilityai/stable-diffusion-2-1", "prompthero/openjourney"

# Replicate API (pay-as-you-go, ~$0.001 per image)
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
REPLICATE_MODEL = "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c47161d6b2c2d2e"


# ================================================================
# IMAGE GENERATOR CLASS
# ================================================================
class ImageGenerator:
    def __init__(self, provider: str = None):
        self.provider = provider or IMAGE_PROVIDER
        
        if self.provider == "local":
            self._init_local()
        elif self.provider == "replicate":
            self._init_replicate()
        else:
            self.provider = "huggingface"
            self._init_huggingface()
    
    def _init_local(self):
        """Initialize local Stable Diffusion (requires GPU recommended)"""
        try:
            from diffusers import StableDiffusionPipeline
            import torch
            
            self.pipe = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                low_cpu_mem_usage=True
            )
            if torch.cuda.is_available():
                self.pipe = self.pipe.to("cuda")
            print("[ImageGen] Local Stable Diffusion initialized.")
        except ImportError:
            print("[ImageGen] diffusers not installed. Falling back to HuggingFace API.")
            self.provider = "huggingface"
            self._init_huggingface()
        except Exception as e:
            print(f"[ImageGen] Local init failed: {e}. Falling back to HuggingFace API.")
            self.provider = "huggingface"
            self._init_huggingface()
    
    def _init_huggingface(self):
        """Initialize HuggingFace Inference API (free tier)"""
        self.api_url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
        self.headers = {"Authorization": f"Bearer {HF_API_TOKEN}"} if HF_API_TOKEN else {}
        print("[ImageGen] HuggingFace Inference API initialized.")
    
    def _init_replicate(self):
        """Initialize Replicate API (pay-as-you-go)"""
        try:
            import replicate
            self.replicate_client = replicate
            print("[ImageGen] Replicate API initialized.")
        except ImportError:
            print("[ImageGen] Replicate not installed. Falling back to HuggingFace API.")
            self.provider = "huggingface"
            self._init_huggingface()
    
    def generate(self, prompt: str, negative_prompt: str = "", width: int = 512, height: int = 512) -> Optional[str]:
        """Generate an image from text prompt. Returns image URL or base64 string."""
        
        if self.provider == "local":
            return self._generate_local(prompt, negative_prompt, width, height)
        elif self.provider == "replicate":
            return self._generate_replicate(prompt, negative_prompt, width, height)
        else:
            return self._generate_huggingface(prompt, negative_prompt, width, height)
    
    def _generate_local(self, prompt, negative_prompt, width, height):
        """Generate using local Stable Diffusion"""
        try:
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=30,
            )
            image = result.images[0]
            
            # Save to bytes and encode as base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
        except Exception as e:
            print(f"[ImageGen] Local generation failed: {e}")
            return None
    
    def _generate_huggingface(self, prompt, negative_prompt, width, height):
        """Generate using HuggingFace Inference API (free)"""
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
            else:
                print(f"[ImageGen] HF API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"[ImageGen] HF API generation failed: {e}")
            return None
    
    def _generate_replicate(self, prompt, negative_prompt, width, height):
        """Generate using Replicate API (pay-as-you-go)"""
        try:
            output = self.replicate_client.run(
                REPLICATE_MODEL,
                input={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "num_inference_steps": 30,
                }
            )
            if output and len(output) > 0:
                return output[0]  # URL to the generated image
            return None
        except Exception as e:
            print(f"[ImageGen] Replicate generation failed: {e}")
            return None


# ================================================================
# HELPER: Generate images for a campaign
# ================================================================
def generate_campaign_images(prompt: str, num_images: int = 3) -> list:
    """Generate multiple images for a campaign"""
    generator = ImageGenerator()
    images = []
    
    # Create variations with different prompts
    variations = [
        f"{prompt}, professional photography, high quality",
        f"{prompt}, creative, artistic, vibrant colors",
        f"{prompt}, minimalistic, clean, modern"
    ]
    
    for i in range(min(num_images, len(variations))):
        img = generator.generate(variations[i])
        if img:
            images.append(img)
    
    return images