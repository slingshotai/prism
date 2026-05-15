# PRISM — Video Data Pipeline

**Splits a social media video into its structured components.** One URL in → transcript, scenes, keyframes, metadata, comments out.

The infrastructure layer that powers Slingshot's video-analysis skills (MAGPIE, me-ig, sfv, agc-idea, etc.).

**Version:** 0.1.0 (renamed from `igap`)
**Distribution:** Free — included with any Slingshot skill that touches video.

---

## What you get from one URL

```
output/<YYYY-MM-DD>_<platform>_<id>/
├── data.json              # metadata + caption + transcript + scenes + comments
└── keyframes/
    ├── scene_001.jpg
    └── ...
```

The `data.json` includes:
- Full text transcript (AssemblyAI) + sentence-level timestamps
- Per-scene timing + paired keyframe path + transcript-segment overlap
- Metadata (creator, title, duration, view/like/comment counts, etc.)
- Caption + hashtags
- Comments (YouTube only — IG doesn't expose them publicly)

Lens skills (MAGPIE etc.) consume this to produce analyses.

## Install

```bash
# 1. Prerequisites
brew install ffmpeg python@3.12

# 2. Clone PRISM (free)
git clone https://github.com/slingshotai/prism ~/dev/slingshot/prism

# 3. Set up the venv
cd ~/dev/slingshot/prism
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4. Add AssemblyAI key to your shell (one-time):
echo 'export ASSEMBLYAI_API_KEY="your_key_from_assemblyai.com"' >> ~/.zshrc
source ~/.zshrc
```

Get a key at https://www.assemblyai.com/dashboard/signup (free trial, then ~$0.015/min).

## Usage

Direct:
```bash
cd ~/dev/slingshot/prism
.venv/bin/python prism.py "https://www.instagram.com/reel/DYPykkUshK2/"
```

With Safari cookies (for IG URLs that need login):
```bash
.venv/bin/python prism.py "https://www.instagram.com/reel/XXX/" --cookies-from-browser safari
```

Output lands in `~/dev/slingshot/prism/output/`. The folder name is `<date>_<platform>_<id>`.

## Via Slingshot skills

Most users invoke PRISM through a lens skill rather than directly:
- **MAGPIE** — discovery + analyse pipeline; runs PRISM as Stage C of the workflow
- **me-ig, sfv, agc-idea, veg-idea, ep-guest** — single-video analytical lenses

Those skills know where PRISM lives and shell out automatically.

## Output format spec

```json
{
  "metadata": {
    "url": "https://www.instagram.com/reel/...",
    "platform": "instagram",
    "creator": "TreatBox ®",
    "title": "Video by treatbox",
    "duration_seconds": 4.945,
    "downloaded_at": "2026-05-15T14:15:53.699916+00:00",
    "like_count": 1230,
    "view_count": null,
    "comment_count": 6,
    "upload_date": "20260512"
  },
  "caption": "anyone else? 🤷🏻‍♀️",
  "hashtags": [],
  "transcript": {
    "full_text": "",
    "segments": []
  },
  "scenes": [
    {
      "number": 1,
      "start": 0.0,
      "end": 5.06,
      "duration": 5.06,
      "keyframe": "keyframes/scene_001.jpg",
      "transcript_segment": ""
    }
  ],
  "comments": []
}
```

## Costs per run

- **AssemblyAI transcription**: ~$0.015/min of audio (a 60-second reel costs ~$0.015; a visual-only reel with no speech transcribes but returns empty segments — same cost)
- **yt-dlp download**: free
- **ffmpeg processing**: local CPU only, no API cost
- **YouTube comments fetch**: free (yt-dlp built-in)

Typical Instagram reel: ~$0.01-$0.02 end-to-end.

## Troubleshooting

**"ASSEMBLYAI_API_KEY not set"** — Set the env var per the install steps, then `source ~/.zshrc` (or restart your terminal).

**"FFmpeg not found"** — `brew install ffmpeg`.

**Instagram download fails with 401/403/login error** — Retry with `--cookies-from-browser safari` (or chrome/firefox). yt-dlp will read cookies from a logged-in browser.

**Transcript is empty** — The video has no speech (music-only, visual-only). The pipeline still completes successfully and you get scenes + keyframes; transcript section is just empty.

## Support

Hit reply on any SlingshotAI transmission, or email matt@aurioncompany.com.

---

© Aurion Digital 2026
