# Subtitle Sync Agent Helper

A small Python script for syncing a translated `.srt` file with a movie. It
tries a synced English subtitle track as the timing reference first. Audio sync
is a separate fallback, so you can tell which route produced the output.
Original files are not overwritten.

## What It Does

`ffsubsync` already does the hard alignment work. This script wraps it for the
common movie-folder case where the video may already contain a synced English
subtitle track. In that case, the English subtitle is used only as a timing
reference for the target subtitle, usually a translated one.

It handles the surrounding chores:

- find the movie in a folder
- find the target subtitle, or ask you to disambiguate
- use embedded English subtitle timing as the first reference
- fall back to an external English `.srt` timing reference
- print the exact `ffsubsync` command
- write a new `_sync.srt` file instead of touching originals

Audio sync is still available. Use it when no synced subtitle reference exists,
or when the reference subtitle is wrong.

Hard ffsubsync cases can use the same recovery knobs you would use manually:
larger max offsets, golden-section framerate search, disabled framerate fixing,
and alternate voice activity detectors.

## Requirements

- macOS, Linux, or another environment with Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- `ffsubsync`

If `ffsubsync` is missing, the script installs it into:

```sh
~/.local/share/ffsubsync-venv
```

This leaves Homebrew/system Python alone. The install step still needs Python's
`venv` module, pip, and access to PyPI.

## Quick Start

```sh
./sync_subtitle_folder.py "/path/to/movie folder"
```

If the folder has multiple subtitle files:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" --subtitle "Movie pt-BR.srt"
```

Preview the command without creating anything:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" --dry-run
```

Write a machine-readable plan:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --doctor \
  --report-json sync_report.json
```

## Reference Strategy

By default, the script looks for a subtitle timing reference:

```text
movie folder
    |
    v
largest video file
    |
    v
target .srt
    |
    v
embedded synced English subtitle?  -> use --reference-stream s:N
    |
    no
    v
external synced English .srt?      -> use that .srt as reference
    |
    no
    v
stop with a clear next command
```

If the video has an unlabeled subtitle stream and you know it is the right
reference, choose it explicitly:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --subtitle "Movie pt-BR.srt" \
  --reference s:0
```

Use audio sync explicitly:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --subtitle "Movie pt-BR.srt" \
  --reference-mode audio
```

Allow automatic audio fallback:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" --reference-mode auto
```

## Recovery Strategy

If the first result is still wrong, classify the failure before making another
file:

- constant early/late shift: use `--offset`
- gets worse over time: try `--gss` or `--no-fix-framerate`
- off by more than a minute: try `--max-offset-seconds 600`
- audio sync fails: try another VAD such as `--vad=webrtc` or `--vad=auditok`
- reference subtitle is suspicious: choose another `--reference` or use audio

For a slower single-pass recovery profile:

```sh
./sync_subtitle_folder.py "/Movies/Example" \
  --subtitle "Example pt-BR.srt" \
  --reference-mode audio \
  --try-harder
```

`--try-harder` adds `--max-offset-seconds 600` and `--gss` unless you already
supplied those options. Audio mode defaults to `auditok`, but you can switch
VADs explicitly. You can also pass safe ffsubsync options directly:

```sh
./sync_subtitle_folder.py "/Movies/Example" \
  --subtitle "Example pt-BR.srt" \
  --reference-mode audio \
  --engine-arg=--strict
```

The wrapper rejects engine args that would override inputs, outputs, overwrite
behavior, or reference-stream selection.

## Doctor Reports

`--doctor` prints the selected video, target subtitle, reference, output path,
and exact `ffsubsync` command without writing a subtitle file. Add
`--report-json` when an agent or script should consume the plan:

```sh
./sync_subtitle_folder.py "/Movies/Example" \
  --subtitle "Example pt-BR.srt" \
  --doctor \
  --report-json sync_report.json
```

The report is a structured execution plan. It does not yet verify playback
quality or score residual sync.

## Common Commands

Sync one subtitle:

```sh
./sync_subtitle_folder.py "/Movies/Example" --subtitle "Example pt-BR.srt"
```

Sync all non-English subtitle candidates:

```sh
./sync_subtitle_folder.py "/Movies/Example" --all
```

Use a specific reference file:

```sh
./sync_subtitle_folder.py "/Movies/Example" \
  --subtitle "Example pt-BR.srt" \
  --reference "Example eng.srt"
```

Create an offset variant after syncing:

```sh
./sync_subtitle_folder.py "/Movies/Example" \
  --subtitle "Example pt-BR_sync.srt" \
  --offset -1.2 \
  --output "Example pt-BR_sync_minus1.2s.srt"
```

Sync against audio:

```sh
./sync_subtitle_folder.py "/Movies/Example" \
  --subtitle "Example pt-BR.srt" \
  --reference-mode audio
```

## Options

```text
folder                 Folder containing the movie and subtitle.
--video VIDEO          Video filename/path. Defaults to the largest video.
--subtitle SUBTITLE    Target subtitle filename/path.
--output OUTPUT        Output subtitle filename/path.
--suffix SUFFIX        Output suffix. Default: _sync.
--offset OFFSET        Extra offset seconds, for example -1.2.
--force                Overwrite the chosen output path.
--dry-run              Print the command without running it.
--doctor               Print a sync plan and imply --dry-run.
--report-json PATH     Write a machine-readable sync plan/report JSON file.
--engine-arg ARG       Pass one safe raw argument to ffsubsync. Repeatable.
--try-harder           Add --max-offset-seconds 600 and --gss.
--max-offset-seconds N Pass ffsubsync --max-offset-seconds.
--no-fix-framerate     Pass ffsubsync --no-fix-framerate.
--gss                  Pass ffsubsync --gss.
--vad VAD              Pass ffsubsync --vad when syncing against audio.
--reference REF        Explicit reference .srt or stream, for example s:0.
--all                  Sync all non-English subtitle candidates.
--reference-mode MODE  subtitle, embedded, external, audio, or auto.
```

## Agent Usage

When asking an agent to run this, point it at [SKILL.md](SKILL.md). Installing
the skill alone does not install the script; the repo must also be available on
the machine. The intended loop is:

1. Run `--doctor --report-json sync_report.json` from the repo root.
2. Use `--reference-mode subtitle`, which is the default.
3. Run the sync without overwriting originals.
4. If the user says it is off, classify constant offset versus drift, bad
   reference, large offset, or audio/VAD failure.
5. Use `--offset` only for constant early/late errors.
6. Use `--try-harder`, `--gss`, `--no-fix-framerate`, `--max-offset-seconds`, or
   `--vad` for known ffsubsync failure modes.
7. If subtitle-reference sync is not enough, rerun with `--reference-mode audio`.
8. Always report the final command and output path.

## Limitations

- Only `.srt` subtitles are supported.
- Language detection uses file names and video metadata. Ambiguous folders need
  `--subtitle`, `--video`, `--reference`, or `--all`.
- The script cannot tell whether the result looks right in your player. It can
  choose references and run `ffsubsync`; you still need to inspect doubtful
  cases.
- Embedded subtitle metadata can be wrong. Use `--reference-mode audio` when the
  supposed English timing reference is not actually synced.

## Development

Run tests:

```sh
python3 -m unittest discover -s tests
```

Check the CLI without writing output:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" --dry-run
```

## License

MIT.

## About Contributions

Please don't take this the wrong way, but I do not accept outside contributions
for any of my projects. I simply don't have the mental bandwidth to review
anything, and it's my name on the thing, so I'm responsible for any problems it
causes; thus, the risk-reward is highly asymmetric from my perspective. I'd also
have to worry about other "stakeholders," which seems unwise for tools I mostly
make for myself for free. Feel free to submit issues, and even PRs if you want
to illustrate a proposed fix, but know I won't merge them directly. Instead,
I'll have Claude or Codex review submissions via `gh` and independently decide
whether and how to address them. Bug reports in particular are welcome. Sorry if
this offends, but I want to avoid wasted time and hurt feelings. I understand
this isn't in sync with the prevailing open-source ethos that seeks community
contributions, but it's the only way I can move at this velocity and keep my
sanity.
