# Subtitle Sync Agent Helper

A small Python helper for syncing translated `.srt` subtitles against a movie,
with an agent-friendly workflow: use a synced English subtitle track as the
timing reference first, keep audio sync as an explicit fallback, and never
overwrite the original files.

## Why This Exists

`ffsubsync` is excellent, but the best reference is often already inside the
movie: a perfectly synced English subtitle track. This script automates the
boring parts around that workflow:

- finds the movie in a folder
- finds the target subtitle, or asks you to disambiguate
- uses embedded English subtitle timing as the first reference
- falls back to an external English `.srt` timing reference
- prints the exact `ffsubsync` command it ran
- writes a new `_sync.srt` file instead of touching originals

Audio sync is available, but it is deliberately opt-in. If the subtitle timing
reference gives a suspicious result, an agent can rerun with audio or create
small offset variants.

## Requirements

- macOS, Linux, or another environment with Python 3
- `ffmpeg` and `ffprobe` on `PATH`
- `ffsubsync`

If `ffsubsync` is missing, the script installs it into:

```sh
~/.local/share/ffsubsync-venv
```

This avoids modifying Homebrew/system Python.

## Quick Start

```sh
./sync_subtitle_folder.py "/path/to/movie folder"
```

If the folder has multiple subtitle files:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" --subtitle "Movie pt-BR.srt"
```

Preview what it would do without creating anything:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" --dry-run
```

## Reference Strategy

Default mode is `subtitle`:

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

To opt into audio sync:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" \
  --subtitle "Movie pt-BR.srt" \
  --reference-mode audio
```

To allow automatic audio fallback:

```sh
./sync_subtitle_folder.py "/path/to/movie folder" --reference-mode auto
```

## Common Commands

Sync one subtitle:

```sh
./sync_subtitle_folder.py "/Movies/Example" --subtitle "Example pt-BR.srt"
```

Sync all non-English subtitle candidates:

```sh
./sync_subtitle_folder.py "/Movies/Example" --all
```

Create an offset variant after syncing:

```sh
./sync_subtitle_folder.py "/Movies/Example" \
  --subtitle "Example pt-BR_sync.srt" \
  --offset -1.2 \
  --output "Example pt-BR_sync_minus1.2s.srt"
```

Use audio explicitly:

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
--all                  Sync all non-English subtitle candidates.
--reference-mode MODE  subtitle, embedded, external, audio, or auto.
```

## Agent Workflow

Use [SKILL.md](SKILL.md) when asking an agent to run this. The skill captures
the intended loop:

1. Dry-run the folder.
2. Use `--reference-mode subtitle`, the default subtitle-timing reference route.
3. Run the sync without overwriting originals.
4. If the user says it is off, make small offset variants.
5. If subtitle-reference sync is not enough, rerun with `--reference-mode audio`.
6. Always report the final command and output path.

## Limitations

- Only `.srt` subtitles are supported.
- Language detection uses file names and video metadata; ambiguous folders need
  `--subtitle`, `--video`, or `--all`.
- The script cannot visually verify sync quality. It can choose references and
  run `ffsubsync`, but a human or agent still needs to inspect suspicious cases.
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
