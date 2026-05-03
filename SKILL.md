---
name: subtitle-sync-agent-helper
description: Use when a user asks an agent to sync translated subtitles with a movie folder, especially when the movie may contain a synced English subtitle track that should be used as the timing reference. Helps run sync_subtitle_folder.py, use subtitle timing references, create offset variants, and avoid modifying originals.
---

# Subtitle Sync Agent Helper

Use the local `sync_subtitle_folder.py` script as the deterministic executor.
Keep the agent work focused on selecting files, choosing the next reference
strategy, interpreting results, and reporting exact commands.

## Workflow

1. Identify the movie folder, target subtitle, and video.
2. Run a dry run first:

   ```sh
   ./sync_subtitle_folder.py "/path/to/movie folder" --dry-run
   ```

3. If the folder is ambiguous, rerun with `--subtitle`, `--video`, or `--all`.
4. Run the default sync first. It uses `--reference-mode subtitle`, which:
   - uses embedded English subtitle timing as the first reference for the target subtitle
   - then tries an external English `.srt` timing reference
   - stops before audio fallback
5. If the right reference is known but not auto-detected, pass it explicitly:
   `--reference s:0` for a stream or `--reference "Movie eng.srt"` for a file.
6. Never modify the original video or subtitle. Let the script write `_sync.srt`
   or pass an explicit `--output`.
7. Report the output path and exact command.

## When The User Says It Is Still Off

Prefer reversible follow-up files:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --subtitle "Movie pt-BR_sync.srt" \
  --offset -1.2 \
  --output "Movie pt-BR_sync_minus1.2s.srt"
```

Use positive offsets to make subtitles later. Use negative offsets to make them
earlier.

## Audio Fallback

Use audio sync only when:

- no synced English subtitle timing reference exists
- the English subtitle timing reference is known to be bad
- the user explicitly asks to try audio

Command pattern:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --subtitle "Movie pt-BR.srt" \
  --reference-mode audio
```

## Reporting Checklist

Always include:

- reference used
- output file
- exact command
- whether originals were preserved
- any offset applied
