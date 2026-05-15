---
status: backlog
urgency: low
importance: medium
---

# Video Post Analyser

## Commander's Intent

**Purpose:** Analyse social media videos (Instagram Reels, TikTok, YouTube Shorts) to extract reusable content patterns - just like we do with text posts, but for video.

**End State:** A web app where you paste a URL, and get back a structured breakdown: scene-by-scene timing, transcript, visual analysis, and psychology - with a reusable template extracted.

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│  Next.js Frontend (Vercel)                  │
│  - URL input form                           │
│  - Analysis display                         │
│  - History of past analyses                 │
└──────────────┬──────────────────────────────┘
               │ API call
┌──────────────▼──────────────────────────────┐
│  Python Backend (Railway)                   │
│                                             │
│  1. Download video (yt-dlp)                 │
│  2. Extract audio (FFmpeg)                  │
│  3. Transcribe (Whisper API)                │
│  4. Detect scenes (FFmpeg scenedetect)      │
│  5. Extract keyframes (FFmpeg)              │
│  6. Analyse visuals (Claude Vision API)     │
│  7. Psychology analysis (Claude API)        │
│  8. Return structured JSON                  │
└─────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js + Tailwind | Consistent with existing projects |
| Frontend hosting | Vercel | Standard |
| Backend | Python (FastAPI) | Best ecosystem for video processing |
| Backend hosting | Railway | Needs FFmpeg binary + temp file storage |
| Video download | yt-dlp | Open source, supports Instagram/TikTok/YouTube |
| Audio extraction | FFmpeg | Industry standard |
| Transcription | OpenAI Whisper API | Best accuracy, returns word-level timestamps |
| Scene detection | FFmpeg `select='gt(scene,0.3)'` | No extra dependency, built into FFmpeg |
| Keyframe extraction | FFmpeg | Extract one frame per detected scene |
| Visual analysis | Claude API (vision) | Best multimodal reasoning |
| Psychology analysis | Claude API | Feed structured data + playbook context |
| Database | Supabase (PostgreSQL) | Store analyses for reference |
| File storage | Supabase Storage or S3 | Temp video/keyframe storage |

## Detailed Pipeline

### Step 1: Video Download

**Input:** Instagram/TikTok/YouTube URL
**Output:** Video file (MP4) in temp storage
**Tool:** yt-dlp

```python
import yt_dlp

def download_video(url: str, output_path: str) -> dict:
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'best[ext=mp4]',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return {
            'title': info.get('title'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader'),
            'platform': info.get('extractor'),
            'description': info.get('description'),
        }
```

**Edge cases:**
- Private accounts: will fail - return clear error
- Stories/disappearing content: may not work
- Rate limiting: add retry logic with backoff
- Instagram login requirement: some content needs cookies (yt-dlp supports `--cookies` flag)

### Step 2: Audio Extraction

**Input:** MP4 file
**Output:** WAV audio file
**Tool:** FFmpeg

```python
import subprocess

def extract_audio(video_path: str, audio_path: str):
    subprocess.run([
        'ffmpeg', '-i', video_path,
        '-vn',                    # no video
        '-acodec', 'pcm_s16le',  # WAV format
        '-ar', '16000',           # 16kHz (Whisper optimal)
        '-ac', '1',               # mono
        audio_path
    ], check=True)
```

### Step 3: Transcription

**Input:** WAV audio file
**Output:** Transcript with word-level timestamps
**Tool:** OpenAI Whisper API

```python
from openai import OpenAI

def transcribe(audio_path: str) -> dict:
    client = OpenAI()
    with open(audio_path, 'rb') as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"]
        )
    return {
        'full_text': result.text,
        'segments': [
            {
                'start': seg.start,
                'end': seg.end,
                'text': seg.text
            }
            for seg in result.segments
        ],
        'words': [
            {
                'start': word.start,
                'end': word.end,
                'word': word.word
            }
            for word in result.words
        ]
    }
```

### Step 4: Scene Detection

**Input:** MP4 file
**Output:** List of scene boundaries with timestamps and durations
**Tool:** FFmpeg scene detection filter

```python
import subprocess
import json

def detect_scenes(video_path: str, threshold: float = 0.3) -> list:
    """
    Uses FFmpeg's scene detection filter.
    threshold: 0.0-1.0, lower = more sensitive (more scenes detected)
    0.3 is a good starting point for social media content.
    """
    cmd = [
        'ffmpeg', '-i', video_path,
        '-filter:v', f"select='gt(scene,{threshold})',showinfo",
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse scene change timestamps from FFmpeg output
    scenes = [0.0]  # Always start at 0
    for line in result.stderr.split('\n'):
        if 'showinfo' in line and 'pts_time:' in line:
            pts_time = float(line.split('pts_time:')[1].split()[0])
            scenes.append(pts_time)

    # Get video duration
    duration = get_video_duration(video_path)
    scenes.append(duration)

    # Build scene list with durations
    scene_list = []
    for i in range(len(scenes) - 1):
        scene_list.append({
            'scene_number': i + 1,
            'start': round(scenes[i], 2),
            'end': round(scenes[i + 1], 2),
            'duration': round(scenes[i + 1] - scenes[i], 2)
        })

    return scene_list
```

### Step 5: Keyframe Extraction

**Input:** MP4 file + scene timestamps
**Output:** One JPEG image per scene (taken from middle of each scene)
**Tool:** FFmpeg

```python
def extract_keyframes(video_path: str, scenes: list, output_dir: str) -> list:
    """Extract one frame from the middle of each scene."""
    keyframes = []
    for scene in scenes:
        # Take frame from middle of scene
        timestamp = scene['start'] + (scene['duration'] / 2)
        output_path = f"{output_dir}/scene_{scene['scene_number']:03d}.jpg"

        subprocess.run([
            'ffmpeg', '-ss', str(timestamp),
            '-i', video_path,
            '-frames:v', '1',
            '-q:v', '2',
            output_path
        ], check=True)

        keyframes.append({
            'scene_number': scene['scene_number'],
            'timestamp': timestamp,
            'path': output_path
        })

    return keyframes
```

### Step 6: Visual Analysis (per scene)

**Input:** Keyframe image + scene metadata
**Output:** Description of what's in each scene
**Tool:** Claude API with vision

```python
import anthropic
import base64

def analyse_scene_visual(image_path: str, scene: dict, transcript_segment: str) -> dict:
    client = anthropic.Anthropic()

    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",  # Sonnet for speed/cost on bulk scenes
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                },
                {
                    "type": "text",
                    "text": f"""Analyse this video frame. Scene duration: {scene['duration']}s.
Transcript during this scene: "{transcript_segment}"

Describe in 2-3 sentences:
1. Shot type (talking head, b-roll, text card, product shot, screen recording, etc.)
2. Composition (close-up, mid-shot, wide, etc.)
3. Key visual elements (text overlays, graphics, background, lighting, colours)
4. Subject's expression/energy if person is visible

Be specific and concise. This is for content pattern analysis."""
                }
            ]
        }]
    )

    return {
        'scene_number': scene['scene_number'],
        'description': response.content[0].text
    }
```

### Step 7: Psychology Analysis (full video)

**Input:** All previous data combined
**Output:** Complete structured analysis
**Tool:** Claude API (Opus for depth of analysis)

```python
def analyse_psychology(
    video_metadata: dict,
    scenes: list,
    transcript: dict,
    visual_analyses: list,
    playbook_context: str
) -> dict:
    client = anthropic.Anthropic()

    # Build the analysis prompt with all data
    scene_breakdown = ""
    for scene, visual in zip(scenes, visual_analyses):
        # Find transcript text that overlaps with this scene
        scene_text = get_transcript_for_timerange(
            transcript, scene['start'], scene['end']
        )
        scene_breakdown += f"""
### Scene {scene['scene_number']} ({scene['start']}s - {scene['end']}s) | Duration: {scene['duration']}s
**Visual:** {visual['description']}
**Transcript:** "{scene_text}"
"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"""You are a social media content strategist analysing a video post.

## Video Metadata
- Platform: {video_metadata['platform']}
- Creator: {video_metadata['uploader']}
- Duration: {video_metadata['duration']}s
- Total scenes: {len(scenes)}

## Scene-by-Scene Breakdown
{scene_breakdown}

## Full Transcript
{transcript['full_text']}

## Content Playbook Context
{playbook_context}

## Your Analysis

Provide a structured analysis covering:

### 1. Hook Analysis (first 3 seconds)
- What stops the scroll?
- Visual hook vs audio hook vs text hook?
- How quickly is the value proposition established?

### 2. Structure Map
For each scene, explain the PURPOSE (not just what's in it):
- Why this scene is here
- Why it's this length
- How it connects to the next scene

### 3. Pacing Analysis
- Average scene duration
- Where pacing speeds up/slows down and why
- Rhythm pattern (e.g., fast-fast-slow, building tension, etc.)

### 4. Psychological Patterns
- Which persuasion principles are at play?
- How is authority/credibility established?
- What emotional journey does the viewer take?
- How are silent viewers served (text overlays)?

### 5. Platform Optimisation
- How is this optimised for the specific platform?
- Aspect ratio, text placement for UI elements
- Loop potential (does the end connect to the beginning?)

### 6. Reusable Template
Extract a scene-by-scene template with:
- Timing for each section
- Shot type
- Purpose
- Placeholders for different topics

Format: detailed markdown."""
        }]
    )

    return {
        'analysis': response.content[0].text
    }
```

### Step 8: Assemble Final Output

Combine everything into a structured JSON response:

```python
{
    "metadata": {
        "url": "https://instagram.com/reel/...",
        "platform": "instagram",
        "creator": "danielpriestley",
        "duration_seconds": 47,
        "total_scenes": 12,
        "avg_scene_duration": 3.9,
        "analysed_at": "2026-02-13T19:00:00Z"
    },
    "transcript": {
        "full_text": "...",
        "segments": [...]
    },
    "scenes": [
        {
            "number": 1,
            "start": 0.0,
            "end": 3.2,
            "duration": 3.2,
            "visual_description": "Talking head, direct to camera...",
            "transcript": "I don't know how closely...",
            "purpose": "Hook - pattern interrupt with urgency"
        }
    ],
    "analysis": {
        "hook": "...",
        "structure_map": "...",
        "pacing": "...",
        "psychology": "...",
        "platform_optimisation": "...",
        "reusable_template": "..."
    }
}
```

## API Endpoints

### Backend (FastAPI)

```
POST /api/analyse
  Body: { "url": "https://instagram.com/reel/..." }
  Response: Full analysis JSON (above)
  Note: This is a long-running request (30-60s). Use polling or SSE.

GET /api/analyse/{id}
  Response: Stored analysis by ID

GET /api/analyses
  Response: List of past analyses (paginated)
```

### Frontend Pages

```
/                   - URL input + recent analyses
/analysis/{id}      - Full analysis view
```

## Frontend Design

### Input Page
- Single URL input field (large, centered)
- "Analyse" button
- Platform auto-detected from URL
- Loading state: progress bar showing pipeline stages
  - "Downloading video..."
  - "Extracting audio..."
  - "Transcribing..."
  - "Detecting scenes..."
  - "Analysing visuals..."
  - "Running psychology analysis..."
- Recent analyses listed below

### Analysis Page
- Video embed (if possible) or thumbnail
- Metadata bar (creator, platform, duration, scene count)
- Tab layout:
  - **Overview**: Hook analysis + psychology + reusable template
  - **Scene Breakdown**: Timeline view with scene cards
  - **Transcript**: Full transcript with scene markers
  - **Template**: Extracted reusable structure

## Database Schema (Supabase)

```sql
CREATE TABLE analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT NOT NULL,
  platform TEXT NOT NULL,
  creator TEXT,
  duration_seconds FLOAT,
  total_scenes INTEGER,
  metadata JSONB,
  transcript JSONB,
  scenes JSONB,
  analysis JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Environment Variables

```
# Backend (.env)
OPENAI_API_KEY=          # Whisper API
ANTHROPIC_API_KEY=       # Claude API (vision + analysis)

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=     # Backend URL on Railway
SUPABASE_URL=
SUPABASE_ANON_KEY=
```

## Dependencies

### Backend (Python)
```
fastapi
uvicorn
yt-dlp
anthropic
openai
python-multipart
```

System packages (Railway Dockerfile):
```
ffmpeg
```

### Frontend (Node)
```
next
tailwindcss
@supabase/supabase-js
```

## Cost Estimate Per Analysis

| Component | Cost |
|-----------|------|
| Whisper API (60s audio) | ~$0.006 |
| Claude Sonnet vision (12 scenes) | ~$0.15 |
| Claude Opus psychology analysis | ~$0.10 |
| Railway compute (~60s) | ~$0.001 |
| **Total per analysis** | **~$0.26** |

At 10 analyses/day = ~$2.60/day = ~$78/month

## Build Order

### Phase 1: Standalone Python Script (Proof of Concept)

Goal: validate the pipeline works and produces useful output. No server, no web framework. Just a script you run from terminal.

```
python analyse.py "https://instagram.com/reel/ABC123"
```

Output: markdown file saved to disk with full analysis.

**Steps:**
1. Create project folder with `analyse.py` and `requirements.txt`
2. Implement `download_video()` - yt-dlp downloads to a temp folder
3. Implement `extract_audio()` - FFmpeg strips audio to WAV
4. Implement `transcribe()` - Whisper API returns timestamped transcript
5. Implement `detect_scenes()` - FFmpeg scene filter returns cut points
6. Implement `extract_keyframes()` - FFmpeg grabs one frame per scene
7. Implement `analyse_visuals()` - loop through keyframes, send each to Claude Sonnet vision
8. Implement `analyse_psychology()` - send all data to Claude Opus for full breakdown
9. Implement `save_output()` - write structured markdown to disk
10. Wire all functions together in `main()`
11. Test with 3-4 different videos (Instagram reel, TikTok, YouTube Short)
12. Review output quality - is the analysis actually useful?

**Requirements:**
- Python 3.10+
- FFmpeg installed locally (`brew install ffmpeg`)
- `.env` file with `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`

**requirements.txt:**
```
yt-dlp
openai
anthropic
python-dotenv
```

**File structure:**
```
video-analyser/
├── analyse.py          # Main script - single entry point
├── requirements.txt
├── .env                # API keys
├── output/             # Generated analyses saved here
└── temp/               # Temp video/audio/keyframe files (auto-cleaned)
```

**Decision gate:** After Phase 1, review the output from 3-4 test videos. If the analysis quality is good, proceed to Phase 2. If not, tune the prompts and scene detection threshold before investing in infrastructure.

### Phase 2: Wrap in FastAPI + Deploy

Goal: make the script accessible as an API so the web frontend can call it.

1. Refactor `analyse.py` functions into a `pipeline/` module
2. Create `server.py` with FastAPI
3. Add `POST /api/analyse` endpoint (calls the pipeline)
4. Add `GET /api/health` endpoint
5. Add progress tracking (SSE or polling) since analysis takes 30-60s
6. Create Dockerfile with FFmpeg + Python deps
7. Deploy to Railway
8. Test endpoint from Postman/curl

**File structure:**
```
video-analyser/
├── server.py           # FastAPI app
├── pipeline/
│   ├── __init__.py
│   ├── download.py
│   ├── audio.py
│   ├── transcribe.py
│   ├── scenes.py
│   ├── visuals.py
│   └── psychology.py
├── analyse.py          # CLI still works (imports from pipeline/)
├── Dockerfile
├── requirements.txt
└── .env
```

### Phase 3: Frontend

Goal: paste a URL in a browser, see the analysis.

1. Create Next.js app
2. Build URL input page (single field, large, centered)
3. Build loading/progress state showing pipeline stages
4. Build analysis display page (tabs: Overview, Scenes, Transcript, Template)
5. Connect to backend API
6. Deploy to Vercel

### Phase 4: Storage & History

Goal: save analyses so you can reference them later.

1. Set up Supabase (PostgreSQL + Storage)
2. Store analyses on completion
3. Add history/list view to frontend
4. Add ability to re-analyse a URL

### Phase 5: Polish

Goal: handle edge cases and improve usability.

1. Error handling (private accounts, rate limits, unsupported URLs)
2. Platform-specific adaptations (different analysis prompts per platform)
3. Export analysis as markdown (for pasting into playbook notes)
4. Optional: integrate with playbook files directly

## Known Limitations

- **Instagram private accounts** won't work without authentication cookies
- **Instagram rate limiting** may throttle downloads if used heavily
- **Video processing time** is ~30-60 seconds per analysis (not instant)
- **Scene detection threshold** may need tuning per content type (talking head vs fast cuts)
- **Cost scales with scene count** - a 60-scene TikTok costs more than a 5-scene reel
- **yt-dlp breaks periodically** when platforms change their APIs - needs maintenance

## Future Ideas

- Batch analysis (analyse 10 videos from one creator, identify their patterns)
- Comparative analysis (compare two creators' styles)
- Auto-populate playbook files from analyses
- Browser extension: right-click "Analyse this video"
- Cohort tool: analyse competitors' best-performing content
