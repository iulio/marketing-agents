import os
import time
import base64
from typing import List, Optional
from google import genai
from google.genai import types
from .cloud_llm import get_cloud_llm

class AIVideoGenerator:
    """Generates videos using Google's Veo 2.0 via the Gemini API, optimized for ad conversions."""
    
    @staticmethod
    def optimize_prompt(base_prompt: str) -> str:
        """Use Gemini to optimize the video prompt for maximum client conversion."""
        llm = get_cloud_llm(temperature=0.7)
        optimization_prompt = f"""
        You are an expert video ad director and conversion rate optimizer.
        Enhance the following video description to make it a highly engaging, conversion-optimized video ad prompt for an AI video generator (like Veo).
        Focus on strong visual hooks, dynamic motion, emotional resonance, and a clear call-to-action aesthetic.
        Keep the prompt under 500 characters, focusing purely on visual and motion descriptions.
        
        Original description: {base_prompt}
        
        Optimized Prompt:
        """
        response = llm.invoke(optimization_prompt)
        return response.content.strip()

    @staticmethod
    def generate(prompt: str, optimize: bool = True) -> List[str]:
        """
        Generate a video using Veo 2.0 and return a list of base64-encoded video URIs.
        """
        final_prompt = AIVideoGenerator.optimize_prompt(prompt) if optimize else prompt
        
        project_id = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", os.getenv("GCP_LOCATION", "us-central1"))
        
        if not project_id:
            # Fallback for testing/local
            print("[VideoGen] ⚠️ GCP_PROJECT_ID not set - returning mock video.")
            return ["data:video/mp4;base64,AAAAHGZ0eXBtcDQyAAAAAW1wNDJpc29t..."]
            
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
        
        try:
            operation = client.models.generate_videos(
                model='veo-2.0-generate-001',
                prompt=final_prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    person_generation="ALLOW_ADULT"
                )
            )
            
            # Poll for completion
            while not operation.done:
                time.sleep(5)
                operation = client.operations.get(operation=operation)
                
            if operation.error:
                raise RuntimeError(f"Video generation failed: {operation.error}")
                
            result = getattr(operation, 'response', None) or getattr(operation, 'result', None)
            if not result or not result.generated_videos:
                raise RuntimeError("No videos generated in the response.")
                
            video_urls = []
            for generated_video in result.generated_videos:
                if generated_video.video.video_bytes:
                    b64_vid = base64.b64encode(generated_video.video.video_bytes).decode('utf-8')
                    video_urls.append(f"data:video/mp4;base64,{b64_vid}")
                elif generated_video.video.uri:
                    video_urls.append(generated_video.video.uri)
            return video_urls
            
        except Exception as e:
            print(f"[VideoGen] ❌ Error generating video: {e}")
            raise
