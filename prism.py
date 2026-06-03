#!/usr/bin/env python3
"""PRISM — splits a social media video into its structured components.

Takes one video URL and produces: full transcript (AssemblyAI), scene
boundaries, keyframe images, metadata, and comments. The data layer
that lens skills (MAGPIE, me-ig, sfv, agc-idea, etc.) consume to do
content analysis.

Output: one folder per run containing data.json + keyframes/.

Usage:
    python prism.py "https://instagram.com/reel/ABC123"
    python prism.py "https://youtube.com/shorts/XYZ789"
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp
from dotenv import load_dotenv
import assemblyai as aai


# ---------------------------------------------------------------------------
# Progress output
# ---------------------------------------------------------------------------

TOTAL_STEPS = 6

def print_step(step: int, label: str):
    """Print a step header."""
    print(f"[{step}/{TOTAL_STEPS}] {label}...", end="", flush=True)


def print_done(elapsed: float):
    """Print completion with elapsed time."""
    print(f"  done ({elapsed:.1f}s)")


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------

def check_prerequisites():
    """Verify FFmpeg and API key are available."""
    if not shutil.which("ffmpeg"):
        print("Error: FFmpeg not found.")
        print("Install with: brew install ffmpeg")
        sys.exit(1)

    load_dotenv()  # project-root .env (back-compatible)
    # Machine-local secrets kept OUTSIDE any repo, so API keys never live inside
    # the shippable skill. Authoritative when present (overrides a stale/blank
    # shell var). Honours $SLINGSHOT_SECRETS, else ~/.config/slingshot/secrets.env.
    _secrets = os.getenv("SLINGSHOT_SECRETS") or os.path.expanduser(
        "~/.config/slingshot/secrets.env"
    )
    if os.path.exists(_secrets):
        load_dotenv(_secrets, override=True)
    if not os.getenv("ASSEMBLYAI_API_KEY"):
        print("Error: ASSEMBLYAI_API_KEY not set.")
        print("Export it in your shell, add it to .env, or put it in "
              "~/.config/slingshot/secrets.env (see .env.example).")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Step 1: Download video
# ---------------------------------------------------------------------------

def download_video(url: str, temp_dir: Path, cookies_from_browser: str | None = None) -> dict:
    """Download video with yt-dlp. Returns metadata + file path."""
    # First extract info to get video ID without downloading
    extract_opts = {"quiet": True, "no_warnings": True}
    if cookies_from_browser:
        extract_opts["cookiesfrombrowser"] = (cookies_from_browser,)
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    video_id = info.get("id", "unknown")
    video_path = temp_dir / f"{video_id}.mp4"

    # Skip download if already exists
    if video_path.exists():
        print(f"  (cached)", end="", flush=True)
    else:
        ydl_opts = {
            "outtmpl": str(video_path),
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        if cookies_from_browser:
            ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    # Extract hashtags from tags list
    hashtags = [tag for tag in info.get("tags", []) or []]

    return {
        "video_path": str(video_path),
        "video_id": video_id,
        "metadata": {
            "url": url,
            "platform": info.get("extractor", "unknown").lower(),
            "creator": info.get("uploader"),
            "title": info.get("title"),
            "duration_seconds": info.get("duration"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "like_count": info.get("like_count"),
            "view_count": info.get("view_count"),
            "comment_count": info.get("comment_count"),
            "upload_date": info.get("upload_date"),
        },
        "caption": info.get("description") or "",
        "hashtags": hashtags,
    }


# ---------------------------------------------------------------------------
# Step 2: Extract audio
# ---------------------------------------------------------------------------

def extract_audio(video_path: str, temp_dir: Path) -> str:
    """Extract audio as 16kHz mono WAV (compact + speech-optimised)."""
    video_id = Path(video_path).stem
    audio_path = temp_dir / f"{video_id}.wav"

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn",                   # no video
            "-acodec", "pcm_s16le",  # WAV format
            "-ar", "16000",          # 16kHz
            "-ac", "1",              # mono
            str(audio_path),
        ],
        capture_output=True,
        check=True,
    )
    return str(audio_path)


# ---------------------------------------------------------------------------
# Step 3: Transcribe
# ---------------------------------------------------------------------------

def transcribe(audio_path: str) -> dict:
    """Transcribe audio with AssemblyAI (universal-3-pro, sentence-level segments)."""
    aai.settings.api_key = os.environ["ASSEMBLYAI_API_KEY"]
    config = aai.TranscriptionConfig(speech_models=["universal-3-pro"])
    transcript = aai.Transcriber().transcribe(audio_path, config=config)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI transcription failed: {transcript.error}")

    segments = []
    try:
        for sent in transcript.get_sentences():
            segments.append({
                "start": round(sent.start / 1000, 2),
                "end": round(sent.end / 1000, 2),
                "text": sent.text.strip(),
            })
    except Exception:
        if transcript.words:
            for word in transcript.words:
                segments.append({
                    "start": round(word.start / 1000, 2),
                    "end": round(word.end / 1000, 2),
                    "text": word.text,
                })

    return {
        "full_text": transcript.text,
        "segments": segments,
    }


# ---------------------------------------------------------------------------
# Step 4: Scene detection
# ---------------------------------------------------------------------------

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def detect_scenes(video_path: str, threshold: float = 0.3) -> list:
    """Detect scene boundaries using FFmpeg's scene filter."""
    result = subprocess.run(
        [
            "ffmpeg", "-i", video_path,
            "-filter:v", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )

    # Parse scene change timestamps from FFmpeg stderr
    scene_times = [0.0]
    for line in result.stderr.split("\n"):
        if "showinfo" in line and "pts_time:" in line:
            pts_time = float(line.split("pts_time:")[1].split()[0])
            scene_times.append(pts_time)

    duration = get_video_duration(video_path)
    scene_times.append(duration)

    # Build scene list
    scenes = []
    for i in range(len(scene_times) - 1):
        scenes.append({
            "number": i + 1,
            "start": round(scene_times[i], 2),
            "end": round(scene_times[i + 1], 2),
            "duration": round(scene_times[i + 1] - scene_times[i], 2),
        })

    # If no scene changes detected, return the whole video as one scene
    if len(scenes) == 1 and scenes[0]["duration"] == round(duration, 2):
        pass  # already correct — single scene spanning full video

    return scenes


# ---------------------------------------------------------------------------
# Step 5: Extract keyframes
# ---------------------------------------------------------------------------

def extract_keyframes(video_path: str, scenes: list, keyframes_dir: Path) -> list:
    """Extract one keyframe from the midpoint of each scene."""
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    keyframes = []

    for scene in scenes:
        timestamp = scene["start"] + (scene["duration"] / 2)
        filename = f"scene_{scene['number']:03d}.jpg"
        output_path = keyframes_dir / filename

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "2",
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

        keyframes.append({
            "scene_number": scene["number"],
            "timestamp": round(timestamp, 2),
            "path": f"keyframes/{filename}",
        })

    return keyframes


# ---------------------------------------------------------------------------
# Step 6: Extract comments (YouTube only)
# ---------------------------------------------------------------------------

def extract_comments(url: str, platform: str, max_comments: int = 100, cookies_from_browser: str | None = None) -> list:
    """Extract comments via yt-dlp. Works for YouTube; returns empty for Instagram."""
    if "instagram" in platform:
        return []

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "getcomments": True,
    }
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        raw_comments = info.get("comments") or []

        comments = []
        for c in raw_comments[:max_comments]:
            comments.append({
                "author": c.get("author", ""),
                "text": c.get("text", ""),
                "likes": c.get("like_count", 0),
                "is_reply": c.get("parent", "root") != "root",
            })

        # Sort by likes descending so the most-engaged comments come first
        comments.sort(key=lambda x: x["likes"], reverse=True)
        return comments

    except Exception:
        # Comments are a nice-to-have — don't fail the pipeline
        return []


# ---------------------------------------------------------------------------
# Transcript-scene matching
# ---------------------------------------------------------------------------

def get_transcript_for_scene(transcript: dict, start: float, end: float) -> str:
    """Find transcript segments that overlap with a scene's time range."""
    matching = []
    for seg in transcript["segments"]:
        # Segment overlaps if it starts before scene ends AND ends after scene starts
        if seg["start"] < end and seg["end"] > start:
            matching.append(seg["text"])
    return " ".join(matching).strip() if matching else ""


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

def assemble_output(
    metadata: dict,
    caption: str,
    hashtags: list,
    transcript: dict,
    scenes: list,
    keyframes: list,
    comments: list,
    output_dir: Path,
):
    """Build data.json combining all pipeline outputs."""
    # Match keyframes and transcript segments to scenes
    keyframe_map = {kf["scene_number"]: kf["path"] for kf in keyframes}

    enriched_scenes = []
    for scene in scenes:
        enriched_scenes.append({
            "number": scene["number"],
            "start": scene["start"],
            "end": scene["end"],
            "duration": scene["duration"],
            "keyframe": keyframe_map.get(scene["number"], ""),
            "transcript_segment": get_transcript_for_scene(
                transcript, scene["start"], scene["end"]
            ),
        })

    data = {
        "metadata": metadata,
        "caption": caption,
        "hashtags": hashtags,
        "transcript": transcript,
        "scenes": enriched_scenes,
        "comments": comments,
    }

    output_file = output_dir / "data.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_file


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PRISM — split social media video into structured components"
    )
    parser.add_argument("url", help="Instagram Reel or YouTube Short URL")
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Browser to extract cookies from (e.g. safari, chrome, firefox)",
    )
    args = parser.parse_args()

    check_prerequisites()

    # Set up directories
    base_dir = Path(__file__).parent
    temp_dir = base_dir / "temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        # Step 1: Download
        t0 = time.time()
        print_step(1, "Downloading video")
        dl = download_video(args.url, temp_dir, args.cookies_from_browser)
        print_done(time.time() - t0)

        video_path = dl["video_path"]
        metadata = dl["metadata"]
        caption = dl["caption"]
        hashtags = dl["hashtags"]
        video_id = dl["video_id"]
        platform = metadata["platform"]

        # Step 2: Extract audio
        t0 = time.time()
        print_step(2, "Extracting audio")
        audio_path = extract_audio(video_path, temp_dir)
        print_done(time.time() - t0)

        # Step 3: Transcribe
        t0 = time.time()
        print_step(3, "Transcribing (AssemblyAI)")
        transcript = transcribe(audio_path)
        print_done(time.time() - t0)

        # Step 4: Detect scenes
        t0 = time.time()
        print_step(4, "Detecting scenes")
        scenes = detect_scenes(video_path)
        print_done(time.time() - t0)

        # Step 5: Extract keyframes
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_name = f"{date_str}_{platform}_{video_id}"
        output_dir = base_dir / "output" / output_name
        output_dir.mkdir(parents=True, exist_ok=True)
        keyframes_dir = output_dir / "keyframes"

        t0 = time.time()
        print_step(5, "Extracting keyframes")
        keyframes = extract_keyframes(video_path, scenes, keyframes_dir)
        print_done(time.time() - t0)

        # Step 6: Extract comments
        t0 = time.time()
        print_step(6, "Extracting comments")
        comments = extract_comments(args.url, platform, cookies_from_browser=args.cookies_from_browser)
        elapsed = time.time() - t0
        if "instagram" in platform:
            print(f"  skipped (not available for Instagram)")
        elif not comments:
            print(f"  none found ({elapsed:.1f}s)")
        else:
            print(f"  done ({len(comments)} comments, {elapsed:.1f}s)")

        # Assemble output
        output_file = assemble_output(
            metadata, caption, hashtags, transcript,
            scenes, keyframes, comments, output_dir,
        )

        # Summary
        print()
        print(f"Done! Output saved to {output_dir.relative_to(base_dir)}/")
        print(f"  -> data.json        (metadata + caption + transcript + {len(scenes)} scenes + {len(comments)} comments)")
        print(f"  -> keyframes/       ({len(keyframes)} images)")

    except yt_dlp.utils.DownloadError as e:
        print(f"\nError: Could not download video.")
        print(f"  {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nError: FFmpeg command failed.")
        if e.stderr:
            stderr = e.stderr if isinstance(e.stderr, str) else e.stderr.decode()
            # Print last few lines of stderr for context
            lines = stderr.strip().split("\n")
            for line in lines[-3:]:
                print(f"  {line}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        # Clean up temp files
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
