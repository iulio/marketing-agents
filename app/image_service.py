# app/image_service.py
import os
import base64
import requests
import time
from typing import List, Dict, Any, Optional

try:
    import replicate
except Exception:
    replicate = None


UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "pollinations").strip().lower()


# ================================================================
# POLLINATIONS.AI (FREE, NO API KEY NEEDED)
# ================================================================

def generate_pollinations(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """Generate an image using Pollinations.ai – free, no key needed. Returns base64 data URL."""
    try:
        clean_prompt = prompt.replace(" ", "%20").replace(",", "%2C").replace("&", "%26")
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&nologo=true"
        response = requests.get(url, timeout=60)
        if response.status_code == 200 and response.content:
            b64 = base64.b64encode(response.content).decode()
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[Image] Pollinations error: {e}")
    return None


# ================================================================
# HUGGINGFACE INFERENCE API (FREE WITH TOKEN)
# ================================================================

def generate_huggingface(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """Generate using HuggingFace Inference API (requires token)."""
    if not HUGGINGFACE_API_TOKEN:
        return None
    model = "runwayml/stable-diffusion-v1-5"
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": prompt, "parameters": {"width": width, "height": height}}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        if response.status_code == 200 and response.content:
            b64 = base64.b64encode(response.content).decode()
            return f"data:image/png;base64,{b64}"
        if response.status_code == 503:
            print("[Image] HuggingFace: Model loading, retrying...")
            time.sleep(8)
            retry = requests.post(api_url, headers=headers, json=payload, timeout=90)
            if retry.status_code == 200 and retry.content:
                b64 = base64.b64encode(retry.content).decode()
                return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[Image] HuggingFace error: {e}")
    return None


# ================================================================
# REPLICATE (PAID, BEST QUALITY)
# ================================================================

def generate_replicate(prompt: str) -> Optional[str]:
    """Generate using Replicate API (requires token & paid)."""
    if not REPLICATE_API_TOKEN or replicate is None:
        return None
    try:
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        output = client.run(
            "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c47161d6b2c2d2e",
            input={"prompt": prompt, "width": 512, "height": 512, "num_outputs": 1, "num_inference_steps": 30},
        )
        if output and isinstance(output, list) and output[0]:
            return str(output[0])
    except Exception as e:
        print(f"[Image] Replicate error: {e}")
    return None


# ================================================================
# MAIN GENERATION WITH FALLBACK CHAIN
# ================================================================

def _provider_chain():
    """Return ordered list of (provider_fn, needs_size) based on IMAGE_PROVIDER."""
    pollinations = (generate_pollinations, True)
    huggingface = (generate_huggingface, True)
    replicate = (generate_replicate, False)  # replicate ignores width/height in its own call
    if IMAGE_PROVIDER == "replicate":
        return [replicate, pollinations, huggingface]
    if IMAGE_PROVIDER == "huggingface":
        return [huggingface, pollinations, replicate]
    return [pollinations, huggingface, replicate]


def generate_one_image(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """Try providers in sequence until one succeeds. Returns base64 data URL or remote URL."""
    for provider_fn, needs_size in _provider_chain():
        try:
            if needs_size:
                result = provider_fn(prompt, width, height)
            else:
                result = provider_fn(prompt)
            if result:
                print(f"[Image] OK via {provider_fn.__name__}")
                return result
        except Exception as e:
            print(f"[Image] {provider_fn.__name__} threw: {e}")
        time.sleep(1)
    print("[Image] All providers failed for this prompt")
    return None


def generate_images(prompt: str, num_images: int = 3, width: int = 512, height: int = 512) -> List[str]:
    """Generate multiple images with prompt variations. Returns list of URL strings."""
    images: List[str] = []
    variations = [
        prompt,
        f"{prompt}, professional photography, high resolution, 8k",
        f"{prompt}, creative, artistic, vibrant colors",
        f"{prompt}, minimalistic, clean, modern design",
    ]

    for i in range(num_images):
        variation = variations[i % len(variations)]
        img = generate_one_image(variation, width, height)
        if img:
            images.append(img)
        else:
            placeholder = f"https://via.placeholder.com/{width}x{height}/1f2937/ffffff?text=Image+{i+1}"
            images.append(placeholder)

    if not images:
        for i in range(num_images):
            images.append(f"https://via.placeholder.com/{width}x{height}/1f2937/ffffff?text=No+Image")

    return images


# ================================================================
# UNSPlASH STOCK SEARCH
# ================================================================

def search_unsplash(query: str, per_page: int = 5) -> List[Dict]:
    """Search free stock images from Unsplash."""
    if not UNSPLASH_ACCESS_KEY:
        return []
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    params = {"query": query, "per_page": per_page}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [{
                "id": img["id"],
                "url": img["urls"]["regular"],
                "thumb": img["urls"]["thumb"],
                "alt": img.get("alt_description", query),
                "photographer": img["user"]["name"],
                "source": "unsplash",
            } for img in data.get("results", [])]
    except Exception as e:
        print(f"[Image] Unsplash error: {e}")
    return []


# ================================================================
# SMART IMAGE PROMPT GENERATION
# ================================================================

def generate_image_prompt(client: Dict, creatives: Dict) -> str:
    """Build a descriptive prompt from client profile and ad creatives."""
    industry = client.get("industry", "business")
    tone = client.get("tone_of_voice", "professional")
    product_keywords = client.get("product_keywords", [])
    headlines = [ad.get("headline", "") for ad in creatives.get("google_ads", [])[:2] if ad.get("headline")]
    headline = headlines[0] if headlines else ""

    prompt = f"A professional marketing image for a {industry} business."
    if headline:
        prompt += f" Headline: {headline}."
    if product_keywords:
        prompt += f" Products: {', '.join(product_keywords[:3])}."
    prompt += f" Style: {tone}, high quality, professional photography."
    return prompt


def select_images(client: Dict, creatives: Dict, num_images: int = 3) -> List[Dict]:
    """Generate campaign images with metadata. Returns list of image dicts."""
    prompt = generate_image_prompt(client, creatives)
    image_urls = generate_images(prompt, num_images)
    return [
        {
            "id": f"img_{idx + 1}",
            "url": url,
            "thumb": url,
            "type": "generated",
            "source": "ai_generated",
            "alt": prompt[:100],
            "prompt": prompt,
        }
        for idx, url in enumerate(image_urls)
    ]


# ================================================================
# LEGACY CLASS WRAPPERS (kept for backward compat)
# ================================================================

class StockImageSearch:
    @staticmethod
    def search(query: str, per_page: int = 10) -> List[Dict]:
        return search_unsplash(query, per_page)


class AIImageGenerator:
    @staticmethod
    def generate(prompt: str, negative_prompt: str = "", num_images: int = 2) -> List[str]:
        return generate_images(prompt, num_images)


class SmartImageSelector:
    @staticmethod
    def select_images(campaign_id: str, client: Dict, creatives: Dict, num_images: int = 3) -> List[Dict]:
        images = select_images(client, creatives, num_images)
        for img in images:
            img["id"] = f"generated-{campaign_id}-{img['id']}"
        return images

    @staticmethod
    def generate_image_prompt(client: Dict, creatives: Dict) -> str:
        return generate_image_prompt(client, creatives)
