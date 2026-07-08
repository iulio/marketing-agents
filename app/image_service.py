import base64
import os
import time
from typing import Any, Dict, List, Optional

import requests

try:
    import replicate
except Exception:
    replicate = None


UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "pollinations").strip().lower()


# ================================================================
# STOCK IMAGE PROVIDERS
# ================================================================

class StockImageSearch:
    """Search free stock image providers with graceful fallbacks."""

    @staticmethod
    def search_unsplash(query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        if not UNSPLASH_ACCESS_KEY:
            return []
        try:
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                params={"query": query, "per_page": per_page},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "id": img.get("id"),
                    "url": img.get("urls", {}).get("regular"),
                    "thumb": img.get("urls", {}).get("thumb"),
                    "alt": img.get("alt_description") or query,
                    "photographer": img.get("user", {}).get("name", "Unknown"),
                    "source": "unsplash",
                    "download_url": img.get("links", {}).get("download_location"),
                }
                for img in data.get("results", [])
                if img.get("urls", {}).get("regular")
            ]
        except Exception as exc:
            print(f"[Image] Unsplash search error: {exc}")
            return []

    @staticmethod
    def search_pexels(query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        if not PEXELS_API_KEY:
            return []
        try:
            response = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": per_page},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "id": str(img.get("id")),
                    "url": img.get("src", {}).get("large"),
                    "thumb": img.get("src", {}).get("tiny") or img.get("src", {}).get("medium"),
                    "alt": img.get("alt") or query,
                    "photographer": img.get("photographer", "Unknown"),
                    "source": "pexels",
                    "download_url": img.get("src", {}).get("original"),
                }
                for img in data.get("photos", [])
                if img.get("src", {}).get("large")
            ]
        except Exception as exc:
            print(f"[Image] Pexels search error: {exc}")
            return []

    @staticmethod
    def search_pixabay(query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        if not PIXABAY_API_KEY:
            return []
        try:
            response = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key": PIXABAY_API_KEY,
                    "q": query,
                    "per_page": per_page,
                    "image_type": "photo",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "id": str(img.get("id")),
                    "url": img.get("largeImageURL"),
                    "thumb": img.get("previewURL") or img.get("webformatURL"),
                    "alt": img.get("tags") or query,
                    "photographer": img.get("user", "Unknown"),
                    "source": "pixabay",
                    "download_url": img.get("largeImageURL"),
                }
                for img in data.get("hits", [])
                if img.get("largeImageURL")
            ]
        except Exception as exc:
            print(f"[Image] Pixabay search error: {exc}")
            return []

    @staticmethod
    def search(query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        providers = [
            StockImageSearch.search_unsplash,
            StockImageSearch.search_pexels,
            StockImageSearch.search_pixabay,
        ]
        results: List[Dict[str, Any]] = []
        for provider in providers:
            if len(results) >= per_page:
                break
            try:
                results.extend(provider(query, per_page))
            except Exception as exc:
                print(f"[Image] Stock provider failure: {exc}")
        deduped: List[Dict[str, Any]] = []
        seen = set()
        for item in results:
            key = item.get("url") or item.get("id")
            if key and key not in seen:
                seen.add(key)
                deduped.append(item)
        return deduped[:per_page]


# ================================================================
# AI IMAGE GENERATION PROVIDERS
# ================================================================

def generate_pollinations(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """Generate image using Pollinations.ai (free)."""
    try:
        url = (
            f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
            f"?width={width}&height={height}&nologo=true"
        )
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(response.content).decode()}"
    except Exception as e:
        print(f"[Image] Pollinations error: {e}")
    return None


def generate_huggingface(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """Generate using HuggingFace Inference API (free with token)."""
    if not HUGGINGFACE_API_TOKEN:
        return None
    model = "runwayml/stable-diffusion-v1-5"
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": prompt, "parameters": {"width": width, "height": height}}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            return f"data:image/png;base64,{base64.b64encode(response.content).decode()}"
        if response.status_code == 503:
            time.sleep(5)
            retry = requests.post(api_url, headers=headers, json=payload, timeout=60)
            if retry.status_code == 200:
                return f"data:image/png;base64,{base64.b64encode(retry.content).decode()}"
    except Exception as e:
        print(f"[Image] HuggingFace error: {e}")
    return None


def generate_replicate(prompt: str) -> Optional[str]:
    """Generate using Replicate (paid, high quality)."""
    if not REPLICATE_API_TOKEN or replicate is None:
        return None
    try:
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        output = client.run(
            "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c47161d6b2c2d2e",
            input={"prompt": prompt, "width": 512, "height": 512, "num_outputs": 1},
        )
        if output and isinstance(output, list) and output[0]:
            return str(output[0])
    except Exception as e:
        print(f"[Image] Replicate error: {e}")
    return None


def generate_image(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """Generate a single image with provider fallback chain.

    Tries providers in order: preferred provider first,
    then falls back to free alternatives.
    Returns a base64 data URL or a remote URL, or None on total failure.
    """
    provider = IMAGE_PROVIDER

    # Build the ordered list of providers to try
    if provider == "replicate":
        chain = [generate_replicate, generate_pollinations, generate_huggingface]
    elif provider == "huggingface":
        chain = [generate_huggingface, generate_pollinations, generate_replicate]
    else:
        chain = [generate_pollinations, generate_huggingface, generate_replicate]

    for gen in chain:
        img = gen(prompt, width, height)
        if img:
            return img
    return None


def generate_images(prompt: str, num_images: int = 3) -> List[str]:
    """Generate multiple images with prompt variations."""
    images: List[str] = []
    variations = [
        prompt,
        f"{prompt}, professional photography, high quality",
        f"{prompt}, creative, artistic, vibrant colors",
        f"{prompt}, minimalistic, clean, modern",
    ]
    for i in range(num_images):
        variation = variations[i % len(variations)]
        img = generate_image(variation)
        if img:
            images.append(img)
        if len(images) >= num_images:
            break
    return images


# ================================================================
# LEGACY WRAPPER (used by existing code)
# ================================================================

class AIImageGenerator:
    """Generate campaign images with paid or free providers."""

    @staticmethod
    def generate_replicate(prompt: str, negative_prompt: str = "", num_images: int = 2) -> List[str]:
        if not REPLICATE_API_TOKEN or replicate is None:
            return []
        try:
            client = replicate.Client(api_token=REPLICATE_API_TOKEN)
            output = client.run(
                "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c47161d6b2c2d2e",
                input={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 30,
                    "num_outputs": num_images,
                },
            )
            return [str(item) for item in output or [] if item]
        except Exception as exc:
            print(f"[Image] Replicate generation error: {exc}")
            return []

    @staticmethod
    def generate_huggingface(prompt: str, num_images: int = 2) -> List[str]:
        if not HUGGINGFACE_API_TOKEN:
            return []
        api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
        results: List[str] = []
        for _ in range(num_images):
            try:
                response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=30)
                response.raise_for_status()
                encoded = base64.b64encode(response.content).decode("utf-8")
                results.append(f"data:image/png;base64,{encoded}")
            except Exception as exc:
                print(f"[Image] HuggingFace generation error: {exc}")
        return results

    @staticmethod
    def generate_free(prompt: str, num_images: int = 2) -> List[str]:
        results: List[str] = []
        for _ in range(num_images):
            try:
                response = requests.get(
                    f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=512&height=512&nologo=true",
                    timeout=30,
                )
                response.raise_for_status()
                encoded = base64.b64encode(response.content).decode("utf-8")
                results.append(f"data:image/png;base64,{encoded}")
            except Exception as exc:
                print(f"[Image] Pollinations generation error: {exc}")
        return results

    @staticmethod
    def generate(prompt: str, negative_prompt: str = "", num_images: int = 2) -> List[str]:
        """Generate with fallback chain instead of single-provider-only."""
        results: List[str] = []
        attempts = 0
        max_attempts = num_images * 2  # Allow some room for fallback

        while len(results) < num_images and attempts < max_attempts:
            attempts += 1
            img = generate_image(prompt)
            if img:
                results.append(img)

        return results


# ================================================================
# SMART IMAGE SELECTOR (orchestrates stock + generation)
# ================================================================

class SmartImageSelector:
    """Suggest campaign imagery using stock search first, AI generation second."""

    @staticmethod
    def generate_image_prompt(client: Dict[str, Any], creatives: Dict[str, Any]) -> str:
        industry = str(client.get("industry", "business") or "business").strip().lower()
        tone = str(client.get("tone_of_voice", "professional") or "professional")
        product_keywords = client.get("product_keywords") or []
        headlines = [ad.get("headline", "") for ad in creatives.get("google_ads", [])[:2] if ad.get("headline")]
        headline = headlines[0] if headlines else client.get("client_name", "product")
        keyword_text = ", ".join(product_keywords[:5]) if product_keywords else headline

        prompt_templates = {
            "flower_shop": f"Beautiful premium floral arrangement, romantic boutique setting, {keyword_text}, professional commercial photography, soft lighting, {tone} brand tone.",
            "restaurant": f"Delicious plated food in a welcoming restaurant scene, {keyword_text}, premium food photography, warm lighting, {tone} branding.",
            "real_estate": f"Modern high-value property exterior and interior mood, {keyword_text}, polished real estate photography, golden hour, {tone} visual style.",
            "credit_broker": f"Professional financial consultation scene with trusted advisor, documents and laptop, {keyword_text}, clean corporate photography, {tone} style.",
            "insurance": f"Happy protected family lifestyle image, reassuring and trustworthy, {keyword_text}, commercial lifestyle photography, {tone} tone.",
            "default": f"Professional advertising image for a {industry} business, featuring {keyword_text}, clean modern commercial style, {tone} tone.",
        }
        return prompt_templates.get(industry, prompt_templates["default"])

    @staticmethod
    def select_images(campaign_id: str, client: Dict[str, Any], creatives: Dict[str, Any], num_images: int = 3) -> List[Dict[str, Any]]:
        prompt = SmartImageSelector.generate_image_prompt(client, creatives)
        images: List[Dict[str, Any]] = []

        stock_results = StockImageSearch.search(prompt, per_page=num_images)
        for image in stock_results[:num_images]:
            images.append(
                {
                    "id": image.get("id") or f"stock-{campaign_id}-{len(images) + 1}",
                    "type": "stock",
                    "url": image.get("url"),
                    "thumb": image.get("thumb") or image.get("url"),
                    "source": image.get("source", "stock"),
                    "alt": image.get("alt") or prompt[:120],
                    "photographer": image.get("photographer", "Unknown"),
                    "download_url": image.get("download_url") or image.get("url"),
                }
            )

        if len(images) < num_images:
            generated = AIImageGenerator.generate(prompt, num_images=num_images - len(images))
            for generated_image in generated:
                images.append(
                    {
                        "id": f"generated-{campaign_id}-{len(images) + 1}",
                        "type": "generated",
                        "url": generated_image,
                        "thumb": generated_image,
                        "source": IMAGE_PROVIDER or "ai_generated",
                        "alt": prompt[:120],
                        "photographer": "AI",
                    }
                )

        while len(images) < num_images:
            placeholder_id = f"placeholder-{campaign_id}-{len(images) + 1}"
            placeholder_url = "https://via.placeholder.com/512x512?text=Campaign+Image"
            images.append(
                {
                    "id": placeholder_id,
                    "type": "placeholder",
                    "url": placeholder_url,
                    "thumb": placeholder_url,
                    "source": "placeholder",
                    "alt": prompt[:120],
                    "photographer": "Placeholder",
                }
            )

        return images[:num_images]
