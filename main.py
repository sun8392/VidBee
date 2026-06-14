"""
VidBee AI Automation - Main Entry Point

This script demonstrates the complete AI automation workflow:
1. Analyze video metadata
2. Generate AI-powered image prompts
3. Generate emotional quotes
4. Output paired image-quote content

Usage:
    python main.py --filename "video.mp4" --style anime --count 3
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from image_generator import ImageGenerator
from quote_generator import QuoteGenerator


class VideoAnalyzer:
    """Analyze video files and extract metadata for AI processing."""

    def __init__(self):
        self.supported_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}

    def analyze(self, filepath: str) -> dict:
        """Analyze a video file and return metadata."""
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {filepath}")

        if path.suffix.lower() not in self.supported_extensions:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        stat = path.stat()

        return {
            "filename": path.name,
            "name_without_ext": path.stem,
            "extension": path.suffix,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def extract_keywords(self, filename: str) -> list:
        """Extract keywords from video filename."""
        # Remove common stop words and file extensions
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "this", "that",
            "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "720p", "1080p", "4k",
        }

        # Split by common delimiters
        parts = filename.lower().replace("_", " ").replace("-", " ").split()
        keywords = [p for p in parts if p not in stop_words and len(p) > 2]

        return list(set(keywords))[:10]  # Limit to 10 unique keywords


def generate_output_dir(base_dir: str, prefix: str) -> Path:
    """Generate a unique output directory."""
    output_path = Path(base_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{prefix}_{timestamp}"
    result = output_path / dir_name
    result.mkdir(exist_ok=True)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="VidBee AI Automation - Generate images and quotes from video metadata"
    )
    parser.add_argument("--filename", type=str, help="Path to video file to analyze")
    parser.add_argument("--keywords", type=str, nargs="*", help="Keywords to use for generation")
    parser.add_argument("--style", type=str, default="anime", choices=["anime", "realistic", "semi_realistic"],
                        help="Image generation style")
    parser.add_argument("--count", type=int, default=3, help="Number of images/quotes to generate")
    parser.add_argument("--quote-style", type=str, default="emotional",
                        choices=["emotional", "inspirational", "romantic", "philosophical"],
                        help="Quote generation style")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory")
    parser.add_argument("--generator", type=str, default="openai", choices=["openai", "sd"],
                        help="Image generator to use")

    args = parser.parse_args()

    # Initialize components
    analyzer = VideoAnalyzer()
    image_gen = ImageGenerator(style=args.style, generator_type=args.generator)
    quote_gen = QuoteGenerator(style=args.quote_style)

    # Determine keywords
    if args.filename:
        # Analyze video file
        print(f"📹 Analyzing video: {args.filename}")
        metadata = analyzer.analyze(args.filename)
        print(f"   Name: {metadata['name_without_ext']}")
        print(f"   Size: {metadata['size_mb']} MB")

        keywords = analyzer.extract_keywords(metadata["name_without_ext"])
        print(f"   Extracted keywords: {', '.join(keywords)}")
    elif args.keywords:
        keywords = args.keywords
        print(f"🔑 Using provided keywords: {', '.join(keywords)}")
    else:
        print("❌ Error: Please provide --filename or --keywords")
        sys.exit(1)

    # Generate output directory
    prefix = "_".join(keywords[:3]) if keywords else "ai_automation"
    output_dir = generate_output_dir(args.output_dir, prefix)
    print(f"📁 Output directory: {output_dir}")

    # Generate images
    print(f"🎨 Generating {args.count} images...")
    image_prompts = image_gen.generate_prompts(keywords, count=args.count)
    image_paths = image_gen.generate_images(image_prompts)

    # Generate quotes
    print(f"💬 Generating {args.count} quotes...")
    quotes = quote_gen.generate_quotes(keywords, count=args.count)

    # Save results
    pairing = {
        "video_metadata": {
            "filename": args.filename or "custom",
            "keywords": keywords,
            "generated_at": datetime.now().isoformat(),
        },
        "pairings": [],
    }

    for i, (img_path, quote) in enumerate(zip(image_paths, quotes), 1):
        pairing["pairings"].append({
            "image": str(img_path),
            "quote": quote,
            "prompt": image_prompts[i - 1] if i - 1 < len(image_prompts) else "",
        })
        print(f"   [{i}] Image: {img_path.name}")
        print(f"       Quote: {quote[:50]}...")

    # Save pairing JSON
    pairing_path = output_dir / "pairing.json"
    with open(pairing_path, "w", encoding="utf-8") as f:
        json.dump(pairing, f, ensure_ascii=False, indent=2)

    # Save quotes to text file
    quotes_path = output_dir / "quotes.txt"
    with open(quotes_path, "w", encoding="utf-8") as f:
        for i, quote in enumerate(quotes, 1):
            f.write(f"{i}. {quote}\n\n")

    # Save video metadata
    if args.filename:
        metadata_path = output_dir / "video_info.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Complete! Output saved to: {output_dir}")
    print(f"   - {pairing_path.name} (image-quote pairing)")
    print(f"   - {quotes_path.name} (quotes only)")
    if args.filename:
        print(f"   - video_info.json (video metadata)")


if __name__ == "__main__":
    main()