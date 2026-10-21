"""Download subtitles/transcripts from a YouTube video.

Usage:
    python yt_transcript.py <url-or-id>                 # list languages, pick one interactively
    python yt_transcript.py <url-or-id> --list          # only list available languages
    python yt_transcript.py <url-or-id> --lang en       # download a language directly
    python yt_transcript.py <url-or-id> --lang en --format srt -o out.srt
"""

import argparse
import re
import sys

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import (
    JSONFormatter,
    SRTFormatter,
    TextFormatter,
    WebVTTFormatter,
)

FORMATTERS = {
    "txt": TextFormatter,
    "srt": SRTFormatter,
    "vtt": WebVTTFormatter,
    "json": JSONFormatter,
}

ID_PATTERN = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})")


def extract_video_id(value):
    match = ID_PATTERN.search(value)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    raise ValueError(f"Could not find a YouTube video ID in: {value}")


def get_video_title(video_id):
    try:
        response = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["title"]
    except Exception:
        return None


def safe_filename(name):
    # Remove characters Windows doesn't allow in file names and tidy whitespace.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:150]


def print_languages(transcripts):
    print("Available subtitles:")
    for i, t in enumerate(transcripts, 1):
        kind = "auto-generated" if t.is_generated else "manual"
        print(f"  {i:>2}. {t.language} [{t.language_code}] ({kind})")


def choose_transcript(transcripts):
    while True:
        try:
            choice = input("\nPick a number or language code (blank to quit): ").strip("﻿ \t")
        except EOFError:
            sys.exit(0)
        if not choice:
            sys.exit(0)
        if choice.isdigit() and 1 <= int(choice) <= len(transcripts):
            return transcripts[int(choice) - 1]
        for t in transcripts:
            if t.language_code.lower() == choice.lower():
                return t
        print("Not a valid choice, try again.")


def find_by_code(transcripts, code):
    # Prefer manual subtitles over auto-generated ones for the same language.
    matches = [t for t in transcripts if t.language_code.lower() == code.lower()]
    matches.sort(key=lambda t: t.is_generated)
    if matches:
        return matches[0]
    # Fall back to machine translation if YouTube offers it.
    for t in transcripts:
        if t.is_translatable and any(
            lang.language_code.lower() == code.lower() for lang in t.translation_languages
        ):
            print(f"No '{code}' subtitles; translating from {t.language} instead.")
            return t.translate(code)
    sys.exit(f"No subtitles available for language '{code}'.")


def main():
    parser = argparse.ArgumentParser(description="Download YouTube video subtitles.")
    parser.add_argument("video", help="YouTube URL or 11-character video ID")
    parser.add_argument("--list", action="store_true", help="only list available languages")
    parser.add_argument("--lang", help="language code to download (e.g. en, es, ja)")
    parser.add_argument("--format", choices=FORMATTERS, default="txt", help="output format (default: txt)")
    parser.add_argument("-o", "--output", help="output file (default: <video_id>.<lang>.<format>)")
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.video)
    except ValueError as e:
        sys.exit(str(e))
    try:
        transcripts = list(YouTubeTranscriptApi().list(video_id))
    except Exception as e:
        sys.exit(f"Could not get subtitles for {video_id}: {e}")

    if not transcripts:
        sys.exit("This video has no subtitles.")

    if args.list:
        print_languages(transcripts)
        return

    if args.lang:
        transcript = find_by_code(transcripts, args.lang)
    else:
        print_languages(transcripts)
        transcript = choose_transcript(transcripts)

    try:
        fetched = transcript.fetch()
    except Exception as e:
        reason = type(e).__name__
        if reason in ("IpBlocked", "RequestBlocked"):
            reason += " - YouTube is temporarily blocking requests from your IP; wait a while and retry"
        sys.exit(f"Could not download subtitles: {reason}")
    text = FORMATTERS[args.format]().format_transcript(fetched)

    output = args.output
    if not output:
        output = f"{video_id}.{safe_filename(transcript.language)}.{args.format}"
        title = get_video_title(video_id)
        if title and safe_filename(title):
            output = f"{safe_filename(title)} - {output}"
    with open(output, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved {transcript.language} subtitles to {output}")


if __name__ == "__main__":
    main()
