# Plan Review

## Original Plan

```text
Create a tiny GitHub repo for the subtitle sync helper:
- sync_subtitle_folder.py
- README.md
- SKILL.md

Agent workflow:
- first try embedded English subtitles
- then external English .srt
- then audio sync
- if the user says it is still off, generate offset variants
- never overwrite originals
- always show the final command and output path
```

## Revision 1: Make Audio Fallback Explicit

**Change**

```diff
- Default workflow: embedded English -> external English -> audio sync
+ Default workflow: embedded English -> external English -> stop with guidance
+ Explicit fallback: --reference-mode audio
+ Automatic fallback, when desired: --reference-mode auto
```

**Rationale**

Audio-based sync is slower and can be less predictable than subtitle-to-subtitle
sync when a known-good English subtitle exists. The user intent is also
iterative: try English first, inspect, then decide whether to try audio.
Silently falling through to audio makes it harder to reason about which method
produced the file.

**Implementation**

Added `--reference-mode` with `english-first`, `embedded`, `external`, `audio`,
and `auto`. The default is now `english-first`.

## Revision 2: Keep A Deterministic Script Under The Agent Workflow

**Change**

```diff
- Put most of the behavior in SKILL.md instructions
+ Put file discovery, reference selection, and command construction in Python
+ Use SKILL.md for decision policy and reporting discipline
```

**Rationale**

Agents are good at judgment, but bad at repeatedly reconstructing shell commands
without small mistakes. A script gives deterministic behavior and test coverage.
The skill tells the agent when to use each path and how to handle subjective
feedback like "it is still off."

**Implementation**

Kept `sync_subtitle_folder.py` as the executor and added `SKILL.md` as the
agent operating procedure.

## Revision 3: Add Tests Around The Fragile Heuristics

**Change**

```diff
- No tests; trust manual dry-runs
+ Add unittest coverage for language heuristics, target selection, output naming,
+ reference mode behavior, and command construction
```

**Rationale**

The riskiest code is not the `ffsubsync` call; it is the heuristic layer around
file names and reference choice. Tests protect against regressions like treating
`en pt-BR` as an English reference or silently overwriting an existing output.

**Implementation**

Added `tests/test_sync_subtitle_folder.py` with dependency-free `unittest`
coverage.

## Revision 4: Make Command Transparency A Feature

**Change**

```diff
- Run ffsubsync and only return the output file
+ Always print folder, video, reference, target subtitle, output path, and exact
+ ffsubsync command
+ Support --dry-run for previewing risky folders
```

**Rationale**

Subtitle sync is often trial-and-error. The user and agent both need a clear
audit trail showing what reference was used and what file was produced. This
also makes it easy to copy a command, adjust an offset, or debug a surprising
result.

**Implementation**

The script prints all selected inputs and the quoted command before running.

## Revision 5: Name The Scope Honestly

**Change**

```diff
- Present this as a universal subtitle sync CLI
+ Present this as an agent helper for a common movie-folder workflow
```

**Rationale**

The script is useful, but not universal. It only handles `.srt`, depends on
`ffmpeg`/`ffprobe`, and cannot visually validate quality. Calling it an "agent
helper" sets better expectations and makes the skill central instead of treating
the script as a polished package.

**Implementation**

The README documents limitations, the intended agent workflow, and explicit
fallback paths.

## NOT In Scope

- Full subtitle format support (`.ass`, `.ssa`, `.vtt`): useful later, but not
  needed for the current `.srt` workflow.
- GUI/player integration: sync inspection still belongs in the video player.
- Package publishing: unnecessary until the script stabilizes through repeated
  real use.
- Automatic visual/audio quality verification: valuable, but much larger than
  the initial helper.

## What Already Exists

- `ffsubsync` already performs the actual alignment; this project wraps it
  instead of reimplementing sync logic.
- `ffmpeg`/`ffprobe` already inspect video streams; this project uses `ffprobe`
  JSON output instead of parsing human text.
- Agent judgment already handles subjective feedback; `SKILL.md` captures that
  loop rather than trying to make the CLI guess quality.

## Failure Modes

| Failure mode | Handling |
| --- | --- |
| `ffmpeg` or `ffprobe` missing | Script exits with a clear missing executable message. |
| `ffsubsync` missing | Script installs it into a dedicated user venv. |
| Multiple target subtitles | Script asks for `--subtitle` or `--all`. |
| Existing `_sync.srt` output | Script creates `_sync_2.srt` unless `--force` is passed. |
| No English subtitle reference | Default mode stops and suggests `--reference-mode audio` or `auto`. |
| Bad embedded English metadata | User can force `--reference-mode external` or `audio`. |

## Test Diagram

```text
folder
  |
  +-- video selection
  |     +-- explicit --video
  |     +-- largest video fallback
  |
  +-- subtitle selection
  |     +-- explicit --subtitle
  |     +-- one candidate
  |     +-- --all non-English candidates
  |     +-- ambiguous -> stop
  |
  +-- reference selection
        +-- embedded English
        +-- external English
        +-- audio, only if explicit/auto
        +-- none -> stop
```

Covered by `tests/test_sync_subtitle_folder.py` for the most failure-prone
branches. End-to-end sync remains a manual/integration concern because it needs
real media files.

## Completion Summary

- Step 0: Scope Challenge: minimal repo plus targeted hardening, not a full package
- Architecture Review: 2 major changes implemented
- Code Quality Review: explicit reference modes and tested heuristics added
- Test Review: diagram produced, unit tests added, media E2E deferred
- Performance Review: no new heavy path; audio remains opt-in
- NOT in scope: written
- What already exists: written
- Failure modes: documented
