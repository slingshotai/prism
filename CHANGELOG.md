# Changelog

All notable changes to PRISM will be documented here.
Uses [Semantic Versioning](https://semver.org/) — MAJOR.MINOR.PATCH.

## [0.1.1] — 2026-05-15

### Documentation
- README updated with `PRISM_HOME` env var documentation. Skills that depend on PRISM (MAGPIE, me-ig, sfv, agc-idea, veg-idea, ep-guest) find it via this env var with default `~/dev/slingshot/prism/`. Team members who clone PRISM somewhere else can override by setting `PRISM_HOME` in their shell profile.

No code changes — this is a docs-only release. The pipeline itself is unchanged from v0.1.0.

## [0.1.0] — 2026-05-15

### Renamed from `igap`
This is the first formal release under the PRISM name. The project previously lived at `~/dev/igap/` as `igap` (Instagram-focused name that didn't reflect what the tool actually does — it splits any video into its structured components).

Now lives at `~/dev/slingshot/prism/` as part of the Slingshot ecosystem.

### What's the same as the final `igap` build
- yt-dlp video download (Instagram, YouTube, and everything else yt-dlp supports)
- ffmpeg audio extraction (16kHz mono WAV, speech-optimised)
- AssemblyAI transcription (universal-3-pro model, sentence-level segments)
- ffmpeg scene detection (threshold 0.3)
- ffmpeg keyframe extraction (midpoint of each scene)
- yt-dlp comments (YouTube only — Instagram comments aren't publicly accessible)
- Structured JSON output combining all of the above

### Migrated
- All hardcoded paths in MAGPIE and the 5 lens skills (me-ig, sfv, agc-idea, veg-idea, ep-guest) updated from `/Users/mattedmundson/dev/igap/` to `/Users/mattedmundson/dev/slingshot/prism/`.
- MAGPIE's `igap_runner.py` renamed to `prism_runner.py`, with class/constant names updated.
- The "lens contract" documentation across the ecosystem now uses PRISM.
- SAM update-check table registered PRISM at v0.1.0.
