"""
AI Quote Generator for VidBee Automation

Generates emotional quotes using OpenAI GPT.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class QuoteGenerator:
    """Generate emotional quotes using OpenAI GPT."""

    STYLE_PROMPTS = {
        "emotional": "温柔治愈、情感共鸣、温暖人心",
        "inspirational": "积极向上、激励人心、充满力量",
        "romantic": "浪漫唯美、心动感觉、甜蜜温馨",
        "philosophical": "深度思考、人生哲理、智慧感悟",
    }

    def __init__(self, style: str = "emotional"):
        self.style = style
        self.style_description = self.STYLE_PROMPTS.get(style, self.STYLE_PROMPTS["emotional"])

        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_quotes(self, keywords: list, count: int = 3) -> list:
        """Generate quotes based on keywords."""
        quotes = []

        for i in range(count):
            keyword = keywords[i % len(keywords)] if keywords else "life"
            quote = self._generate_single_quote(keyword)
            quotes.append(quote)

        return quotes

    def _generate_single_quote(self, keyword: str) -> str:
        """Generate a single quote using OpenAI."""
        prompt = f"""Generate a short, beautiful quote in Chinese that incorporates the theme of "{keyword}".

Requirements:
- Style: {self.style_description}
- Length: 15-30 Chinese characters
- Should be original and meaningful
- Output ONLY the quote text, nothing else"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative writer who writes beautiful Chinese quotes."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip().strip('"\'')
        except Exception as e:
            print(f"   Error generating quote: {e}")
            return f"关于{keyword}的温柔语录"