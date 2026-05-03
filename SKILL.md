---
name: subtitle-sync-agent-helper
description: Use when a user asks an agent to sync translated subtitles with a movie folder, especially when the movie may contain a synced English subtitle track that should be used as the timing reference. Helps run sync_subtitle_folder.py, choose subtitle/audio references, use ffsubsync recovery flags, create offset variants, and avoid modifying originals.
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
4. Use this strategy ladder:
   - default subtitle reference: `--reference-mode subtitle`
   - explicit stream/file reference when the right one is known: `--reference s:0`
   - audio fallback: `--reference-mode audio`
   - hard cases: add `--try-harder` or specific ffsubsync recovery flags
   - manual `--offset` only when the remaining error is a constant early/late shift
5. The default subtitle route:
   - uses embedded English subtitle timing as the first reference for the target subtitle
   - then tries an external English `.srt` timing reference
   - stops before audio fallback
6. If the right reference is known but not auto-detected, pass it explicitly:
   `--reference s:0` for a stream or `--reference "Movie eng.srt"` for a file.
7. Never modify the original video or subtitle. Let the script write `_sync.srt`
   or pass an explicit `--output`.
8. Report the output path and exact command.

## When The User Says It Is Still Off

First classify the failure:

- constant early/late shift: create an offset variant
- gets worse over time: try `--gss` or `--no-fix-framerate`
- off by more than a minute: retry with higher `--max-offset-seconds`
- noisy audio route failed: try another VAD such as `--vad=webrtc` or `--vad=auditok`
- subtitle reference may be bad: switch reference or use audio

Prefer reversible follow-up files only for constant offset:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --subtitle "Movie pt-BR_sync.srt" \
  --offset -1.2 \
  --output "Movie pt-BR_sync_minus1.2s.srt"
```

Use positive offsets to make subtitles later. Use negative offsets to make them
earlier.

## Try-Harder Options

Use these when the normal route fails:

- `--try-harder`: adds `--max-offset-seconds 600` and `--gss`
- `--max-offset-seconds 600`: subtitles may be more than 60 seconds off
- `--no-fix-framerate`: disables bad framerate correction guesses
- `--gss`: slower search for a better framerate ratio
- `--vad=webrtc` or `--vad=auditok`: switch VAD when audio sync is wrong
- `--engine-arg=--strict`: pass a safe raw ffsubsync option when needed

Do not pass ffsubsync input, output, overwrite, or reference-stream options with
`--engine-arg`; the wrapper controls those to preserve originals.

## Doctor And Reports

Use doctor mode when you want an agent-readable plan before writing subtitles:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --doctor \
  --report-json sync_report.json
```

The report records the selected reference, engine args, output path, exact
command, and whether the command was planned or run. It is not a playback-quality
verdict yet; use it as evidence for the next step.

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
- strategy used: subtitle, explicit reference, audio, or try-harder fallback
- output file
- exact command
- whether originals were preserved
- any offset applied
- any ffsubsync recovery flags used
- report path, when `--report-json` was used
- next recommended action when confidence is low
