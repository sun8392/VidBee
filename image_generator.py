"""
AI Image Generator for VidBee Automation

Supports OpenAI DALL-E and Stable Diffusion WebUI.
"""

import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class ImageGenerator:
    """Generate AI images using OpenAI DALL-E or Stable Diffusion."""

    STYLES = {
        "anime": {
            "suffix": ", anime style, beautiful girl, vibrant colors, detailed anime art",
            "negative_prompt": "realistic, photorealistic, 3d, render, western cartoon",
        },
        "realistic": {
            "suffix": ", photorealistic, realistic photo, high quality photography",
            "negative_prompt": "anime, cartoon, drawing, painting, illustration, 3d, render",
        },
        "semi_realistic": {
            "suffix": ", semi-realistic art style, detailed illustration, soft lighting",
            "negative_prompt": "anime, overly cartoonish, photorealistic, 3d render",
        },
    }

    def __init__(
        self,
        style: str = "anime",
        generator_type: str = "openai",
        size: str = "512x512",
        output_dir: str = "output/images",
    ):
        self.style = style
        self.generator_type = generator_type
        self.size = size
        self.output_path = Path(output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)

        if generator_type == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        elif generator_type == "sd":
            self.sd_url = os.getenv("SD_WEBUI_URL", "http://127.0.0.1:7860")

    def generate_prompts(self, keywords: list, count: int = 3) -> list:
        """Generate image prompts from keywords."""
        style_config = self.STYLES.get(self.style, self.STYLES["anime"])

        prompts = []
        scenes = [
            "a peaceful garden at sunset",
            "standing by a window on a rainy day",
            "walking through a field of flowers",
            "reading a book in a cozy cafe",
            "watching the stars on a clear night",
            "sitting on a beach at dawn",
            "dancing in the rain",
            "playing with pets in a park",
            "cooking in a warm kitchen",
            "meditating in a serene forest",
        ]

        for i in range(count):
            keyword = keywords[i % len(keywords)] if keywords else "beautiful"
            scene = scenes[i % len(scenes)]
            prompt = f"a beautiful young woman, {keyword}, {scene}{style_config['suffix']}"
            prompts.append(prompt)

        return prompts

    def generate_images(self, prompts: list) -> list:
        """Generate images from prompts."""
        if self.generator_type == "openai":
            return self._generate_with_openai(prompts)
        elif self.generator_type == "sd":
            return self._generate_with_sd(prompts)
        else:
            raise ValueError(f"Unknown generator type: {self.generator_type}")

    def _generate_with_openai(self, prompts: list) -> list:
        """Generate images using OpenAI DALL-E."""
        image_paths = []

        for i, prompt in enumerate(prompts):
            try:
                print(f"   Generating image {i + 1}/{len(prompts)}...")
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size=self.size,
                    n=1,
                    response_format="b64_json",
                )

                image_data = response.data[0].b64_json
                filename = f"image_{i + 1:02d}.png"
                filepath = self.output_path / filename

                import base64
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(image_data))

                image_paths.append(filepath)
                print(f"   Saved: {filepath.name}")

            except Exception as e:
                print(f"   Error generating image {i + 1}: {e}")

        return image_paths

    def _generate_with_sd(self, prompts: list) -> list:
        """Generate images using Stable Diffusion WebUI API."""
        import requests

        image_paths = []
        style_config = self.STYLES.get(self.style, self.STYLES["anime"])

        for i, prompt in enumerate(prompts):
            try:
                print(f"   Generating image {i + 1}/{len(prompts)}...")

                payload = {
                    "prompt": f"{prompt}, masterpiece, best quality, highres",
                    "negative_prompt": f"{style_config['negative_prompt']}, lowres, bad anatomy",
                    "steps": 20,
                    "cfg_scale": 7,
                    "width": int(self.size.split("x")[0]),
                    "height": int(self.size.split("x")[1]),
                }

                response = requests.post(
                    f"{self.sd_url}/sdapi/v1/txt2img",
                    json=payload,
                    timeout=120,
                )
                data = response.json()

                if "images" in data and data["images"]:
                    import base64
                    filename = f"image_{i + 1:02d}.png"
                    filepath = self.output_path / filename

                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(data["images"][0]))

                    image_paths.append(filepath)
                    print(f"   Saved: {filepath.name}")

                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"   Error generating image {i + 1}: {e}")

        return image_paths