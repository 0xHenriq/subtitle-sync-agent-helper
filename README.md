# Subtitle Sync Agent Helper

This repo is retired.

The wrapper script was removed because upstream
[`ffsubsync`](https://github.com/smacke/ffsubsync) already provides the useful
sync behavior directly:

- sync a subtitle against video/audio
- sync a subtitle against a synced reference `.srt`
- use embedded subtitle streams with `--reference-stream s:N`
- apply manual offsets with `--apply-offset-seconds`
- recover hard cases with `--gss`, `--no-fix-framerate`,
  `--max-offset-seconds`, and `--vad`

The durable artifact is now the local agent skill:

```text
/Users/victorwaknin/agent-skills-vault/subtitle-sync/SKILL.md
```

Use that skill when asking an agent to sync subtitles. It tells the agent how
to use `ffsubsync` directly, choose English subtitle references first, preserve
original files, and report the exact command/output.
