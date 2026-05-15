---
name: prism
description: "PRISM — splits a social media video into its structured components. Takes one Instagram/YouTube URL and produces: full transcript (via AssemblyAI), scene boundaries, keyframe images, metadata, and comments. The data layer that powers lens skills (MAGPIE, me-ig, sfv, agc-idea, veg-idea, ep-guest). Use when Matt says 'prism this URL', 'split this video', 'extract data from this reel', 'prism analysis', or directly when a lens skill needs the raw data. NOT a content analyser itself — pair it with a lens skill (igap default, or brand-specific) to get an analytical breakdown. Outputs raw structured data only."
user-invocable: true
argument-hint: "<video_url>"
version: "0.1.0"
---

# PRISM — Video Data Extraction

The infrastructure layer of the Slingshot video ecosystem. Splits one video URL into its structured components: transcript, scenes, keyframes, metadata, comments.

## What this skill does

Given an Instagram Reel or YouTube Short URL, PRISM:

1. Downloads the video via yt-dlp
2. Extracts audio
3. Transcribes via AssemblyAI (universal-3-pro)
4. Detects scene boundaries via FFmpeg
5. Extracts one keyframe per scene
6. Pulls comments (YouTube only — Instagram doesn't expose them publicly)
7. Writes everything to a structured `data.json` + a `keyframes/` folder

PRISM is **the data layer**. It doesn't analyse content — that's what lens skills (MAGPIE for discovery, me-ig for personal brand IG, agc-idea for AGC meetings, sfv for strategy learning, etc.) do.

## Usage

```bash
cd /Users/mattedmundson/dev/slingshot/prism
.venv/bin/python prism.py "https://www.instagram.com/reel/ABC123/"
```

For Instagram URLs that fail with login/permission errors:
```bash
.venv/bin/python prism.py "https://www.instagram.com/reel/ABC123/" --cookies-from-browser safari
```

Output lands in `output/<YYYY-MM-DD>_<platform>_<id>/`.

## Output structure

```
output/<YYYY-MM-DD>_<platform>_<id>/
├── data.json              # metadata + caption + transcript + scenes + comments
└── keyframes/
    ├── scene_001.jpg
    ├── scene_002.jpg
    └── ...
```

`data.json` shape:
```json
{
  "metadata": {
    "url": "...", "platform": "instagram",
    "creator": "...", "title": "...", "duration_seconds": 12.3, ...
  },
  "caption": "...",
  "hashtags": [...],
  "transcript": {
    "full_text": "...",
    "segments": [{ "start": 0.0, "end": 3.2, "text": "..." }]
  },
  "scenes": [
    { "number": 1, "start": 0.0, "end": 3.2, "duration": 3.2,
      "keyframe": "keyframes/scene_001.jpg", "transcript_segment": "..." }
  ],
  "comments": [
    { "author": "...", "text": "...", "likes": 0, "is_reply": false }
  ]
}
```

## Dependencies

- **Python 3.10+** with the requirements in `requirements.txt` (yt-dlp, assemblyai, python-dotenv)
- **ffmpeg** (system install: `brew install ffmpeg`)
- **AssemblyAI API key** as `ASSEMBLYAI_API_KEY` env var (or in `.env` file at the project root). ~$0.015 per minute of audio.

## What this skill does NOT do

- Does NOT produce analytical breakdowns. Pair it with a lens skill.
- Does NOT scrape Instagram comments — IG doesn't expose them publicly. Use Apify if you need IG comments (MAGPIE wires this for you).
- Does NOT support platforms other than what yt-dlp supports (Instagram, YouTube, TikTok, hundreds of others — but tested mostly on IG Reels + YouTube Shorts).

## Consumers

Lens skills that wrap PRISM:
- [[magpie]] — discovery + ranking + analyse pipeline
- me-ig, sfv, agc-idea, veg-idea, ep-guest — brand-specific analytical lenses

Each lens skill follows the contract: "Step 1 runs PRISM, Steps 2+ analyse the resulting folder." This is what makes the MAGPIE `analyse` mode able to invoke any lens programmatically.
