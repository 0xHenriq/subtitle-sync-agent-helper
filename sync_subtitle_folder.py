#!/usr/bin/env python3
"""Sync a subtitle in a movie folder using subtitle timing references first."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import re
import shlex
import shutil
import subprocess
import sys
import venv
from pathlib import Path


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".mov", ".avi", ".webm"}
SUBTITLE_EXTENSIONS = {".srt"}
REFERENCE_MODES = ("subtitle", "embedded", "external", "audio", "auto")
GENERATED_MARKERS = (
    "_sync",
    "_engref_sync",
    "_audio_sync",
    "sincronizada",
    "sincronizado",
    "synchronized",
    "synced",
)
COMMON_NON_ENGLISH_TOKENS = {
    "ar",
    "br",
    "de",
    "es",
    "fr",
    "he",
    "hi",
    "it",
    "ja",
    "ko",
    "nl",
    "pl",
    "pt",
    "ru",
    "tr",
    "zh",
}


@dataclass(frozen=True)
class ReferenceChoice:
    value: str
    label: str


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def quote_command(command: list[str]) -> str:
    return shlex.join(command)


def resolve_in_folder(folder: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = folder / path
    return path.resolve()


def tokens_for(path: Path) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", path.stem.lower()) if token}


def looks_english(path: Path) -> bool:
    tokens = tokens_for(path)
    if "english" in tokens or "eng" in tokens:
        return True
    if "en" in tokens and not (tokens & COMMON_NON_ENGLISH_TOKENS):
        return True
    if "en-us" in path.stem.lower() or "en-gb" in path.stem.lower():
        return True
    return False


def looks_generated(path: Path) -> bool:
    stem = path.stem.lower()
    return any(marker in stem for marker in GENERATED_MARKERS)


def find_video(folder: Path, explicit: str | None) -> Path:
    explicit_path = resolve_in_folder(folder, explicit)
    if explicit_path:
        if not explicit_path.exists():
            raise SystemExit(f"Video not found: {explicit_path}")
        return explicit_path

    candidates = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    if not candidates:
        raise SystemExit(f"No video file found in {folder}")

    return max(candidates, key=lambda path: path.stat().st_size)


def subtitle_candidates(folder: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in SUBTITLE_EXTENSIONS
            and not looks_generated(path)
        ),
        key=lambda path: path.name.lower(),
    )


def find_target_subtitles(folder: Path, explicit: str | None, all_targets: bool) -> list[Path]:
    explicit_path = resolve_in_folder(folder, explicit)
    if explicit_path:
        if not explicit_path.exists():
            raise SystemExit(f"Subtitle not found: {explicit_path}")
        return [explicit_path]

    candidates = subtitle_candidates(folder)
    if not candidates:
        raise SystemExit(f"No .srt subtitle found in {folder}")
    if len(candidates) == 1:
        return candidates

    non_english = [path for path in candidates if not looks_english(path)]
    if all_targets:
        return non_english or candidates
    if len(non_english) == 1:
        return non_english

    choices = "\n".join(f"  - {path.name}" for path in candidates)
    raise SystemExit(
        "More than one possible target subtitle found. "
        "Run again with --subtitle or --all.\n"
        f"{choices}"
    )


def make_output_path(subtitle: Path, suffix: str, explicit: str | None, force: bool) -> Path:
    if explicit:
        output = Path(explicit).expanduser()
        if not output.is_absolute():
            output = subtitle.parent / output
        output = output.resolve()
    else:
        output = subtitle.with_name(f"{subtitle.stem}{suffix}{subtitle.suffix}")

    if force or not output.exists():
        return output

    for index in range(2, 1000):
        candidate = output.with_name(f"{output.stem}_{index}{output.suffix}")
        if not candidate.exists():
            return candidate
    raise SystemExit(f"Could not find an unused output path near {output}")


def ensure_executable(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Required executable not found on PATH: {name}")
    return path


def ensure_ffsubsync() -> str:
    path = shutil.which("ffsubsync")
    if path:
        return path

    venv_dir = Path.home() / ".local" / "share" / "ffsubsync-venv"
    venv_bin = venv_dir / "bin" / "ffsubsync"
    if venv_bin.exists():
        return str(venv_bin)

    print(f"ffsubsync not found; installing into {venv_dir} ...")
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    pip = venv_dir / "bin" / "pip"
    run([str(pip), "install", "ffsubsync"])

    if not venv_bin.exists():
        raise SystemExit("ffsubsync installation finished, but executable was not found.")
    return str(venv_bin)


def ffprobe_streams(video: Path) -> list[dict]:
    ensure_executable("ffprobe")
    result = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            str(video),
        ],
        capture=True,
    )
    return json.loads(result.stdout).get("streams", [])


def stream_text(stream: dict) -> str:
    tags = stream.get("tags", {}) or {}
    pieces = [
        str(tags.get("language", "")),
        str(tags.get("title", "")),
        str(tags.get("handler_name", "")),
    ]
    return " ".join(pieces).lower()


def find_embedded_english_subtitle(video: Path) -> tuple[str, str] | None:
    subtitle_number = 0
    fallback_if_single: tuple[str, str] | None = None
    count = 0

    for stream in ffprobe_streams(video):
        if stream.get("codec_type") != "subtitle":
            continue

        reference_stream = f"s:{subtitle_number}"
        subtitle_number += 1
        count += 1

        text = stream_text(stream)
        if "eng" in text or "english" in text or re.search(r"\ben\b", text):
            return reference_stream, "metadata matched English"

        fallback_if_single = reference_stream, "only embedded subtitle stream"

    if count == 1:
        return fallback_if_single
    return None


def find_external_english_reference(folder: Path, targets: list[Path]) -> Path | None:
    target_paths = {target.resolve() for target in targets}
    candidates = sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in SUBTITLE_EXTENSIONS
            and path.resolve() not in target_paths
            and not looks_generated(path)
            and looks_english(path)
        ),
        key=lambda path: path.name.lower(),
    )
    if len(candidates) == 1:
        return candidates[0]
    return None


def select_reference(
    video: Path,
    folder: Path,
    subtitles: list[Path],
    mode: str,
) -> ReferenceChoice:
    if mode not in REFERENCE_MODES:
        raise SystemExit(f"Unknown reference mode: {mode}")

    if mode in {"subtitle", "embedded", "auto"}:
        embedded = find_embedded_english_subtitle(video)
        if embedded:
            stream, reason = embedded
            return ReferenceChoice(
                value=f"embedded:{stream}",
                label=f"embedded subtitle stream {stream} ({reason})",
            )
        if mode == "embedded":
            raise SystemExit("No embedded English subtitle reference found.")

    if mode in {"subtitle", "external", "auto"}:
        external = find_external_english_reference(folder, subtitles)
        if external:
            return ReferenceChoice(value=str(external), label=f"external subtitle {external}")
        if mode == "external":
            raise SystemExit("No external English .srt reference found.")

    if mode in {"audio", "auto"}:
        return ReferenceChoice(value="audio", label="audio stream a:0")

    raise SystemExit(
        "No synced subtitle timing reference found. "
        "Run again with --reference-mode audio to sync against audio, "
        "or --reference-mode auto to allow audio fallback automatically."
    )


def build_ffsubsync_command(
    ffsubsync: str,
    video: Path,
    subtitle: Path,
    output: Path,
    reference: str,
    offset: float | None,
) -> list[str]:
    command: list[str]

    if reference.startswith("embedded:"):
        stream = reference.split(":", 1)[1]
        command = [
            ffsubsync,
            str(video),
            "--reference-stream",
            stream,
            "-i",
            str(subtitle),
            "-o",
            str(output),
        ]
    elif reference == "audio":
        command = [
            ffsubsync,
            str(video),
            "--reference-stream",
            "a:0",
            "--vad",
            "auditok",
            "-i",
            str(subtitle),
            "-o",
            str(output),
        ]
    else:
        command = [
            ffsubsync,
            reference,
            "-i",
            str(subtitle),
            "-o",
            str(output),
        ]

    if offset is not None and offset != 0:
        command.extend(["--apply-offset-seconds", str(offset)])

    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sync one subtitle in a movie folder. Uses embedded/external English "
            "subtitles as timing references before explicit audio sync."
        )
    )
    parser.add_argument("folder", help="Folder containing the movie and subtitle.")
    parser.add_argument("--video", help="Video filename/path. Defaults to the largest video in the folder.")
    parser.add_argument("--subtitle", help="Target subtitle filename/path. Required if several are ambiguous.")
    parser.add_argument("--output", help="Output subtitle filename/path.")
    parser.add_argument("--suffix", default="_sync", help="Suffix for generated output. Default: _sync")
    parser.add_argument("--offset", type=float, help="Extra offset seconds to apply after syncing, e.g. -1.2")
    parser.add_argument("--force", action="store_true", help="Overwrite the chosen output path if it exists.")
    parser.add_argument("--dry-run", action="store_true", help="Print the command without running it.")
    parser.add_argument(
        "--reference-mode",
        choices=REFERENCE_MODES,
        default="subtitle",
        help=(
            "Reference selection strategy. Default: subtitle, which tries "
            "embedded/external subtitle timing references and stops before audio fallback."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="If several target subtitles are found, sync all non-English candidates.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        raise SystemExit(f"Folder not found: {folder}")

    ensure_executable("ffmpeg")
    ffsubsync = ensure_ffsubsync()

    video = find_video(folder, args.video)
    subtitles = find_target_subtitles(folder, args.subtitle, args.all)
    if args.output and len(subtitles) > 1:
        raise SystemExit("--output can only be used when syncing one subtitle.")

    reference = select_reference(
        video=video,
        folder=folder,
        subtitles=subtitles,
        mode=args.reference_mode,
    )

    print(f"Folder: {folder}")
    print(f"Video: {video}")
    print(f"Reference: {reference.label}")
    for subtitle in subtitles:
        output = make_output_path(subtitle, args.suffix, args.output, args.force)
        command = build_ffsubsync_command(
            ffsubsync=ffsubsync,
            video=video,
            subtitle=subtitle,
            output=output,
            reference=reference.value,
            offset=args.offset,
        )

        print(f"Target subtitle: {subtitle}")
        print(f"Output: {output}")
        print(f"Command: {quote_command(command)}")

        if not args.dry_run:
            run(command)
            print(f"Done: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {quote_command(exc.cmd)}", file=sys.stderr)
        if exc.stdout:
            print(exc.stdout, file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        raise SystemExit(exc.returncode)
