---
name: subtitle-sync-agent-helper
description: Use when a user asks an agent to sync translated subtitles in a movie folder with sync_subtitle_folder.py. Prioritizes synced English subtitle references, safe outputs, ffsubsync recovery flags, doctor reports, and exact command reporting.
---

# Subtitle Sync Agent Helper

This is only a thin agent runbook. Use [README.md](README.md) or
`./sync_subtitle_folder.py --help` for details.

The skill is not the tool. Before running anything, make sure this repo is
available on the machine and run commands from the repo root, or use the full
path to `sync_subtitle_folder.py`.

## Agent Contract

1. Start with a plan:

   ```sh
   ./sync_subtitle_folder.py "/path/to/movie folder" \
     --doctor \
     --report-json sync_report.json
   ```

2. Prefer subtitle timing references before audio:
   - default: `--reference-mode subtitle`
   - known stream/file: `--reference s:0` or `--reference "Movie eng.srt"`
   - no good subtitle reference: `--reference-mode audio`

3. Use `--offset` only for a constant early/late shift.

4. For harder failures, use the wrapper's recovery flags:
   - drift: `--gss` or `--no-fix-framerate`
   - huge offset: `--max-offset-seconds 600`
   - uncertain audio/VAD behavior: `--vad=webrtc` or `--vad=auditok`
   - broad retry: `--try-harder`

5. Preserve originals. Do not pass ffsubsync input, output, overwrite, or
   reference-stream options through `--engine-arg`.

6. Report the reference, strategy, output path, exact command, recovery flags,
   report path if used, and whether originals were preserved.
