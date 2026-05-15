# Video Analysis Modes — Design Document

**Date:** 2026-03-03
**Status:** Approved

## Overview

Expand igap from a single-purpose video analysis tool into a multi-mode system. Four new Claude Code skills, each calling the shared `igap.py` extraction pipeline, then running mode-specific analysis workflows with different outputs.

The existing `/igap` skill stays untouched as the general video analysis tool.

## Architecture: Four Independent Skills

Each mode is a separate Claude Code skill. All share:

- **Extraction pipeline:** `igap.py` at `/Users/mattedmundson/dev/igap/igap.py` — downloads video, extracts audio, transcribes via Whisper, detects scenes, extracts keyframes, pulls comments
- **Output root:** `5.Resources/05.AI/Video Analysis/` with subfolders per mode
- **Invocation pattern:** `/<skill-name> <url>`

### Why separate skills (not one skill with modes)

- Workflows diverge completely after extraction
- User already knows the mode when finding the video
- Skills evolve independently
- Can build and ship incrementally

## Skill 1: `/ep-guest` — EP Guest Research

**Purpose:** Quick vibe check on a potential EP podcast guest found in a video.

**Workflow:**
1. Run `igap.py` to extract video data
2. Identify creator: name, company/brand, role, topic
3. Web search: person + company (LinkedIn, website, press/content)
4. Produce Guest Brief markdown file

**Output format:** `5.Resources/05.AI/Video Analysis/EP Guests/{Creator Name} - Guest Brief.md`

**Guest Brief sections:**
- **Who:** Name, role, company, location
- **What they do:** 2-3 sentences on the company/brand
- **Why they're interesting:** What came through in the video
- **EP fit:** Would their expertise resonate with EP listeners?
- **Reach:** Follower count, audience size indicators
- **Contact:** Email, LinkedIn, website (publicly available)
- **Vibe rating:** Hot / Warm / Cold
- **Video link:** Original URL

**Post-output:** Present brief, ask: reach out, park for later, or pass.

**No playbook updates.** Research tool only.

## Skill 2: `/sfv` — Short Form Video Strategy

**Purpose:** Extract and verify SFV strategies from educational videos, then update relevant playbooks.

**Workflow:**
1. Run `igap.py` to extract video data
2. Extract key strategies/tactics as actionable claims
3. Identify creator credibility + context (platform/niche specificity)
4. Verify each strategy with web research (2-3 sources per claim)
5. Rate each: Verified / Plausible / Dubious
6. Produce SFV Analysis markdown file

**Output format:** `5.Resources/05.AI/Video Analysis/SFV/{YYYY-MM-DD} - {title}.md`

**SFV Analysis sections:**
- **Source:** Video link, creator, date
- **Strategies extracted:** Each with verification status + source links
- **Relevance assessment:** Which accounts/playbooks could benefit
- **Recommended playbook updates:** Specific suggestions

**Post-output:** Discussion — present verified strategies, ask which to apply. For approved strategies, update the relevant playbook with citation.

**Playbooks referenced:**
- `4.Learnings/Marketing/Content/Video/General Video Playbook.md`
- `4.Learnings/Marketing/Content/Video/CROWD Video Playbook.md`
- `4.Learnings/Marketing/Content/Video/between_Sunday Video Playbook.md`
- `4.Learnings/Marketing/Content/Video/Content Ideas Bank.md`

## Skill 3: `/agc-idea` — AGC Business Ideas

**Purpose:** Analyse a video showing an idea/product/strategy relevant to Advent Gift Company (including Seven Yays, Snapify). Produce a visual briefing note for Wednesday AGC meetings.

**Workflow:**
1. Run `igap.py` to extract video data
2. Identify the idea, who's behind it, how it works
3. Web search: company, approach, results/reviews, competitor implementations
4. Produce AGC Idea Brief with embedded keyframe screenshots
5. Copy relevant keyframes to vault Attachments folder

**Output format:** `5.Resources/05.AI/Video Analysis/AGC Ideas/{YYYY-MM-DD} - {Idea title}.md`

**AGC Idea Brief sections:**
- **The Idea:** 2-3 sentence summary
- **Source:** Video link, company name, creator
- **How it works:** Breakdown with embedded keyframe screenshots (`![[image]]` syntax)
- **Why it's relevant to AGC:** Application to SY, Snapify, or AGC
- **What it would take:** Quick win / Medium project / Big lift
- **Questions for Wednesday:** 2-3 discussion prompts

**Image handling:** Keyframes copied to vault `Attachments/` folder for Obsidian embed compatibility.

**No playbook updates.** Standalone brief for team discussion.

## Skill 4: `/me-ig` — Personal Brand Instagram

**Purpose:** Analyse videos in Matt's niche (business, ecommerce, leadership, podcasting) for what works, then generate specific content ideas for the ME IG account.

**Workflow:**
1. Run `igap.py` to extract video data
2. Full video analysis: hook, format/structure, pacing, topic angle, engagement signals
3. Generate 2-3 content ideas for ME IG account (topic, hook, format, angle, effort estimate)
4. Produce ME IG Analysis with embedded keyframes
5. Copy relevant keyframes to vault Attachments
6. Bootstrap/update ME IG Video Playbook

**Output format:** `5.Resources/05.AI/Video Analysis/ME IG/{YYYY-MM-DD} - {title}.md`

**ME IG Analysis sections:**
- **Source video:** Link, creator, metrics
- **Why it works:** Hook, format, pacing, angle, engagement breakdown
- **Content ideas:** 2-3 ideas with topic, hook line, format, angle, effort tag (quick / needs prep / needs B-roll)
- **Keyframe screenshots:** Embedded for visual reference

**Content ideas voice:** Business operator sharing what he's learning. Not guru-mode.

**Playbook handling:**
- First run creates `4.Learnings/Marketing/Content/Video/ME IG Video Playbook.md`
- Subsequent runs ask whether to add new patterns
- Content ideas added to Content Ideas Bank tagged `#me-ig`

## Vault Folder Structure (New)

```
5.Resources/05.AI/Video Analysis/
  EP Guests/
    {Creator Name} - Guest Brief.md
  SFV/
    {YYYY-MM-DD} - {title}.md
  AGC Ideas/
    {YYYY-MM-DD} - {Idea title}.md
  ME IG/
    {YYYY-MM-DD} - {title}.md
```

## Skill File Locations

```
.claude/skills/ep-guest/SKILL.md
.claude/skills/sfv/SKILL.md
.claude/skills/agc-idea/SKILL.md
.claude/skills/me-ig/SKILL.md
```

Existing skill unchanged:
```
.claude/skills/igap/SKILL.md
```

## Build Order

Build incrementally, one skill at a time. Recommended order based on likely usage frequency and complexity:

1. `/ep-guest` — simplest workflow, good for validating the pattern
2. `/sfv` — adds verification + playbook updates
3. `/agc-idea` — adds image embedding
4. `/me-ig` — most complex (analysis + ideation + playbook bootstrapping)
