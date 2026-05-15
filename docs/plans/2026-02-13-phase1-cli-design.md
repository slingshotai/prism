# Phase 1 Design: igap CLI

## What it does

`igap.py` is a CLI tool that takes an Instagram Reel or YouTube Short URL and produces structured data for Claude Code to analyse.

The script handles media processing (download, audio extraction, transcription, scene detection, keyframe extraction). Claude Code handles analysis (visual interpretation, psychology, strategy, template extraction).

This hybrid approach eliminates the need for an Anthropic API key. The only external API call is Whisper for transcription.

## Invocation

```
python igap.py "https://instagram.com/reel/ABC123"
```

Output:
```
[1/5] Downloading video...        done (3.2s)
[2/5] Extracting audio...         done (1.1s)
[3/5] Transcribing (Whisper)...   done (4.7s)
[4/5] Detecting scenes...         done (1.3s)
[5/5] Extracting keyframes...     done (2.0s)

Done! Output saved to output/2026-02-13_instagram_ABC123/
  -> data.json        (metadata + transcript + scenes)
  -> keyframes/       (scene_001.jpg, scene_002.jpg, ...)
```

## Pipeline

```
URL -> yt-dlp -> MP4 -> FFmpeg -> WAV -> Whisper API -> transcript
                  |
               FFmpeg -> scene boundaries -> FFmpeg -> keyframe JPEGs
```

All steps run sequentially with progress printed to stdout.

## Output structure

```
output/2026-02-13_instagram_ABC123/
  data.json
  keyframes/
    scene_001.jpg
    scene_002.jpg
    ...
```

### data.json

```json
{
  "metadata": {
    "url": "https://instagram.com/reel/ABC123",
    "platform": "instagram",
    "creator": "danielpriestley",
    "title": "...",
    "duration_seconds": 47,
    "downloaded_at": "2026-02-13T19:00:00Z"
  },
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
  ]
}
```

Each scene is pre-matched to its overlapping transcript segment.

## Dependencies

### Python (requirements.txt)

```
yt-dlp
openai
python-dotenv
```

No `anthropic` package. No `fastapi`. Minimal.

### System

- Python 3.10+
- FFmpeg (`brew install ffmpeg`)

### Environment (.env)

```
OPENAI_API_KEY=     # Whisper API only
```

## File structure

```
igap/
  igap.py
  requirements.txt
  .env
  output/          # gitignored
  temp/            # gitignored, auto-cleaned
```

## Platforms supported

- Instagram Reels
- YouTube Shorts

TikTok deferred to a later phase.

## Scene detection

FFmpeg scene filter with fixed threshold of 0.3. If zero scenes are detected (common for static talking heads), the entire video is treated as one scene.

## Error handling

Handled:
- Invalid/unsupported URL: clear error message, exit
- Private/unavailable video: clear error message, exit
- FFmpeg not installed: checked at startup before doing anything
- Whisper API failure: catch and print error (auth, rate limit)
- No scenes detected: treat whole video as single scene
- Video already downloaded: skip download if MP4 exists in temp

Not handled (deferred):
- Retry logic / backoff
- Instagram cookie auth
- Rate limiting across runs
- Timeout for very long videos

## Analysis step (Claude Code)

After the script runs, the user asks Claude Code to analyse the output. Claude Code:

1. Reads `data.json` for metadata, transcript, and scene structure
2. Reads each keyframe image
3. Produces a markdown analysis covering:
   - Hook analysis (first 3 seconds)
   - Structure map (purpose of each scene)
   - Pacing analysis (rhythm, tempo changes)
   - Psychological patterns (persuasion, authority, emotional journey)
   - Platform optimisation
   - Reusable template (scene-by-scene with placeholders)

The analysis prompt lives in the conversation, not the script. This allows iteration without code changes and enables follow-up questions.

## Decisions made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Hybrid (Python + Claude Code) | No API key needed for analysis, interactive follow-ups |
| Script structure | Single file | Simplest for Phase 1, modularise in Phase 2 |
| Transcription | Whisper API | Best timestamps, simple, low cost |
| Analysis model | Claude Code (subscription) | Free, interactive, no API key |
| Scene threshold | Fixed 0.3 | Simple, good enough for most content |
| Platforms | Instagram + YouTube | Most common, well-supported by yt-dlp |
| Playbook context | Skipped | Phase 2+ feature |
| Output format | JSON + keyframes | Optimal for Claude Code to consume |
