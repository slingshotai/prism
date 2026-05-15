# igap — Video Content Analyser

A CLI tool that downloads social media videos, extracts structured data (transcript, scenes, keyframes), and prepares everything for Claude Code to analyse and extract reusable content templates.

## Prerequisites

- Python 3.10+ (installed via `brew install python@3.12`)
- FFmpeg (`brew install ffmpeg`)
- An AssemblyAI API key (for transcription)

## Setup

```bash
cd ~/dev/igap

# Create virtual environment (first time only)
python3.12 -m venv .venv

# Install dependencies
.venv/bin/pip install -r requirements.txt

# Add your AssemblyAI API key (or export ASSEMBLYAI_API_KEY in your shell)
cp .env.example .env
# Edit .env and add your key
```

## Usage

### Step 1: Run igap

```bash
.venv/bin/python igap.py "<video-url>"
```

Supported platforms:
- Instagram Reels
- YouTube Shorts

Example:
```bash
.venv/bin/python igap.py "https://www.instagram.com/reel/ABC123"
.venv/bin/python igap.py "https://www.youtube.com/shorts/XYZ789"
```

Output:
```
[1/6] Downloading video...        done (3.2s)
[2/6] Extracting audio...         done (0.1s)
[3/6] Transcribing (AssemblyAI)... done (9.1s)
[4/6] Detecting scenes...         done (1.3s)
[5/6] Extracting keyframes...     done (2.0s)
[6/6] Extracting comments...      done (23 comments, 1.8s)

Done! Output saved to output/2026-02-13_instagram_ABC123/
  -> data.json        (metadata + caption + transcript + 15 scenes + 0 comments)
  -> keyframes/       (15 images)
```

Note: Comments are only available for YouTube. For Instagram, step 6 shows "skipped (not available for Instagram)".

### Step 2: Ask Claude Code to analyse

Open Claude Code and say:

> Analyse the video I just processed in output/2026-02-13_instagram_ABC123/

Claude Code will:
1. Read `data.json` for metadata, caption, transcript, scene structure, and comments
2. For Instagram videos (where comments can't be pulled automatically), offer you the option to paste in any comments you think are interesting. Say "skip" to continue without
3. Read each keyframe image in `keyframes/`
4. Produce a full analysis covering:
   - Hook analysis (first 3 seconds)
   - Structure map (purpose of each scene)
   - Pacing analysis (rhythm, tempo changes)
   - Psychological patterns (persuasion, authority, emotional journey)
   - Caption strategy (how the creator framed the post)
   - Audience language (phrases and questions from comments)
   - Platform optimisation
   - Reusable template (scene-by-scene with placeholders + caption template)

### Step 3: Update playbooks

After the analysis, say:

> Update the playbooks with this template

Claude Code will:
1. Determine if the video reveals a new template or fits an existing one
2. Add, refine, or skip the template in the **General Video Playbook**
3. If applicable, add or update adaptations in CROWD and between_Sunday playbooks
4. **Always** extract content ideas from the transcript, caption, and comments — map them to the relevant accounts and append to the **Content Ideas Bank**

The content ideas step happens every time, even when the playbook doesn't change. A fitness creator's comment section might contain the exact language your faith audience uses about fear and doubt. The ideas bank accumulates across all analyses.

## Playbook and ideas bank locations

```
~/Vaults/My Vault/4.Learnings/Marketing/Content/Video/
  General Video Playbook.md          — All video templates with psychology + examples
  CROWD Video Playbook.md            — Church channel: sermon clips, culture reels, event recaps
  between_Sunday Video Playbook.md   — Matt direct-to-camera: evangelistic, pastoral, personal
  Content Ideas Bank.md              — Running list of hooks, language, and topic ideas from all analyses
```

### Which playbook is which?

| Playbook | Account | Content | Voice |
|----------|---------|---------|-------|
| **General** | Business (LinkedIn, X) | Ecommerce, leadership, podcasting templates | Matt as operator |
| **CROWD** | Crowd Church | Sermon clips, event recaps, culture montages | The church |
| **between_Sunday** | @between_Sunday | Direct-to-camera faith content, outreach, pastoral | Matt as pastor |
| **Content Ideas Bank** | All accounts | Hooks, audience language, topic ideas, theme transfers | — |

## Output structure

Each analysis creates a folder in `output/`:

```
output/2026-02-13_instagram_ABC123/
  data.json           — Metadata, transcript, scene-by-scene breakdown
  keyframes/
    scene_001.jpg     — One frame from the midpoint of each scene
    scene_002.jpg
    ...
```

### data.json format

```json
{
  "metadata": {
    "url": "...",
    "platform": "instagram",
    "creator": "...",
    "title": "...",
    "duration_seconds": 47,
    "downloaded_at": "2026-02-13T19:00:00Z",
    "like_count": 12400,
    "view_count": 284000,
    "comment_count": 312,
    "upload_date": "20260210"
  },
  "caption": "The full post description/caption including #hashtags...",
  "hashtags": ["fitness", "health", "tips"],
  "transcript": {
    "full_text": "...",
    "segments": [
      { "start": 0.0, "end": 3.2, "text": "..." }
    ]
  },
  "scenes": [
    {
      "number": 1,
      "start": 0.0,
      "end": 3.2,
      "duration": 3.2,
      "keyframe": "keyframes/scene_001.jpg",
      "transcript_segment": "..."
    }
  ],
  "comments": [
    {
      "author": "username",
      "text": "This changed my perspective...",
      "likes": 45,
      "is_reply": false
    }
  ]
}
```

Notes:
- `like_count`, `view_count`, `comment_count` may be `null` if the platform doesn't expose them
- `comments` is populated for YouTube only; empty array `[]` for Instagram (API restriction)
- Comments are sorted by likes (most-engaged first), capped at 100

## How it works

```
URL → yt-dlp → MP4 → FFmpeg → WAV → AssemblyAI API → transcript
        ↓        ↓
        ↓     FFmpeg → scene boundaries → FFmpeg → keyframe JPEGs
        ↓
        └→ metadata + caption + hashtags + comments (YouTube only)
```

1. **Download** — yt-dlp downloads the video as MP4 and extracts metadata, caption, and hashtags
2. **Extract audio** — FFmpeg strips audio to 16kHz mono WAV (compact + speech-optimised)
3. **Transcribe** — AssemblyAI (universal-3-pro) returns sentence-level timestamped segments
4. **Detect scenes** — FFmpeg scene filter (threshold 0.3) finds visual cut points
5. **Extract keyframes** — FFmpeg grabs one frame from the midpoint of each scene
6. **Extract comments** — yt-dlp pulls top comments sorted by engagement (YouTube only)

All processing outputs are saved as structured JSON. Claude Code handles the analysis — no Anthropic API key needed.

## Cost

~$0.015 per minute of audio (AssemblyAI). A typical 60-second Reel costs around $0.015.

## Troubleshooting

**"FFmpeg not found"** — Run `brew install ffmpeg`

**"ASSEMBLYAI_API_KEY not set"** — Export `ASSEMBLYAI_API_KEY` in your shell, or create a `.env` file with the key (see `.env.example`)

**403 error on YouTube** — Update yt-dlp: `.venv/bin/pip install --upgrade yt-dlp`

**No scenes detected** — The video has no visual cuts (e.g. a static talking head). The entire video is treated as one scene. This is normal.

**Instagram private account** — Private videos can't be downloaded. The video must be publicly accessible.
