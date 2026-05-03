import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sync_subtitle_folder as sync  # noqa: E402


class SubtitleSyncTests(unittest.TestCase):
    def test_language_heuristics_keep_translated_en_pt_as_target(self):
        self.assertTrue(sync.looks_english(Path("Movie.eng.srt")))
        self.assertTrue(sync.looks_english(Path("Movie English.srt")))
        self.assertFalse(sync.looks_english(Path("Movie en pt-BR.srt")))
        self.assertFalse(sync.looks_english(Path("Movie.pt-BR.srt")))

    def test_find_target_subtitles_requires_specific_choice_when_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "Movie.pt-BR.srt").write_text("1\n", encoding="utf-8")
            (folder / "Movie.es.srt").write_text("1\n", encoding="utf-8")
            (folder / "Movie.eng.srt").write_text("1\n", encoding="utf-8")
            (folder / "Movie.pt-BR_sync.srt").write_text("1\n", encoding="utf-8")

            with self.assertRaises(SystemExit):
                sync.find_target_subtitles(folder, explicit=None, all_targets=False)

            targets = sync.find_target_subtitles(folder, explicit=None, all_targets=True)
            self.assertEqual(
                [target.name for target in targets],
                ["Movie.es.srt", "Movie.pt-BR.srt"],
            )

    def test_output_path_never_overwrites_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            subtitle = Path(tmp) / "Movie.pt-BR.srt"
            subtitle.write_text("1\n", encoding="utf-8")
            (Path(tmp) / "Movie.pt-BR_sync.srt").write_text("old\n", encoding="utf-8")

            output = sync.make_output_path(subtitle, "_sync", explicit=None, force=False)
            self.assertEqual(output.name, "Movie.pt-BR_sync_2.srt")

    def test_output_path_cannot_be_original_even_with_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            subtitle = Path(tmp) / "Movie.pt-BR.srt"
            subtitle.write_text("1\n", encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                sync.make_output_path(subtitle, "_sync", explicit=str(subtitle), force=True)

            self.assertIn("different from the original", str(raised.exception))

    def test_report_path_is_folder_relative(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)

            report_path = sync.resolve_report_path(folder, "sync_report.json")

            self.assertEqual(report_path, (folder / "sync_report.json").resolve())

    def test_report_path_cannot_overwrite_media_or_subtitles(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            video = folder / "Movie.mkv"
            subtitle = folder / "Movie.pt-BR.srt"
            output = folder / "Movie.pt-BR_sync.srt"
            reference = folder / "Movie.eng.srt"
            for path in (video, subtitle, reference):
                path.write_text("x\n", encoding="utf-8")

            choice = sync.ReferenceChoice(value=str(reference), label="reference")

            for protected in (video, subtitle, output, reference):
                with self.subTest(protected=protected.name):
                    with self.assertRaises(SystemExit):
                        sync.validate_report_path(
                            protected,
                            video,
                            [subtitle],
                            [output],
                            choice,
                        )

    def test_subtitle_reference_mode_does_not_fall_back_to_audio(self):
        original_embedded = sync.find_embedded_subtitle_reference
        original_external = sync.find_external_english_reference
        sync.find_embedded_subtitle_reference = lambda video, require_english: None
        sync.find_external_english_reference = lambda folder, targets: None
        try:
            with self.assertRaises(SystemExit) as raised:
                sync.select_reference(
                    video=Path("movie.mkv"),
                    folder=Path("."),
                    subtitles=[Path("Movie.pt-BR.srt")],
                    mode="subtitle",
                )
            self.assertIn("--reference s:N", str(raised.exception))
            self.assertIn("--reference-mode audio", str(raised.exception))

            choice = sync.select_reference(
                video=Path("movie.mkv"),
                folder=Path("."),
                subtitles=[Path("Movie.pt-BR.srt")],
                mode="auto",
            )
            self.assertEqual(choice.value, "audio")
        finally:
            sync.find_embedded_subtitle_reference = original_embedded
            sync.find_external_english_reference = original_external

    def test_embedded_english_detection_uses_specific_metadata(self):
        english_stream = {"tags": {"language": "eng", "title": "English"}}
        english_title_stream = {"tags": {"title": "English / SDH"}}
        noisy_stream = {"tags": {"title": "engineering notes"}}

        self.assertIsNotNone(sync.embedded_subtitle_english_reason(english_stream))
        self.assertIsNotNone(sync.embedded_subtitle_english_reason(english_title_stream))
        self.assertIsNone(sync.embedded_subtitle_english_reason(noisy_stream))

    def test_unknown_single_embedded_stream_requires_embedded_mode(self):
        original_streams = sync.ffprobe_streams
        sync.ffprobe_streams = lambda video: [{"codec_type": "subtitle", "tags": {"title": "Forced"}}]
        try:
            self.assertIsNone(sync.find_embedded_subtitle_reference(Path("movie.mkv"), require_english=True))
            self.assertEqual(
                sync.find_embedded_subtitle_reference(Path("movie.mkv"), require_english=False),
                ("s:0", "only embedded subtitle stream"),
            )
        finally:
            sync.ffprobe_streams = original_streams

    def test_explicit_reference_accepts_stream_or_external_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            reference = folder / "Movie.eng.srt"
            target = folder / "Movie.pt-BR.srt"
            reference.write_text("1\n", encoding="utf-8")
            target.write_text("1\n", encoding="utf-8")

            stream_choice = sync.resolve_explicit_reference(folder, "s:0", [target])
            file_choice = sync.resolve_explicit_reference(folder, "Movie.eng.srt", [target])

            self.assertEqual(stream_choice.value, "stream:s:0")
            self.assertEqual(file_choice.value, str(reference.resolve()))

    def test_embedded_english_reference_builds_ffsubsync_command(self):
        command = sync.build_ffsubsync_command(
            ffsubsync="/bin/ffsubsync",
            video=Path("/movies/Movie.mkv"),
            subtitle=Path("/movies/Movie.pt-BR.srt"),
            output=Path("/movies/Movie.pt-BR_sync.srt"),
            reference="stream:s:0",
            offset=-1.2,
        )

        self.assertEqual(command[0], "/bin/ffsubsync")
        self.assertIn("--reference-stream", command)
        self.assertIn("s:0", command)
        self.assertIn("--apply-offset-seconds", command)
        self.assertIn("-1.2", command)

    def test_audio_stream_reference_uses_auditok(self):
        command = sync.build_ffsubsync_command(
            ffsubsync="/bin/ffsubsync",
            video=Path("/movies/Movie.mkv"),
            subtitle=Path("/movies/Movie.pt-BR.srt"),
            output=Path("/movies/Movie.pt-BR_sync.srt"),
            reference="stream:a:1",
            offset=None,
        )

        self.assertIn("--reference-stream", command)
        self.assertIn("a:1", command)
        self.assertIn("--vad", command)
        self.assertIn("auditok", command)

    def test_engine_args_are_passed_to_ffsubsync(self):
        command = sync.build_ffsubsync_command(
            ffsubsync="/bin/ffsubsync",
            video=Path("/movies/Movie.mkv"),
            subtitle=Path("/movies/Movie.pt-BR.srt"),
            output=Path("/movies/Movie.pt-BR_sync.srt"),
            reference="stream:s:0",
            offset=None,
            engine_args=["--max-offset-seconds", "600", "--gss"],
        )

        self.assertIn("--max-offset-seconds", command)
        self.assertIn("600", command)
        self.assertIn("--gss", command)

    def test_engine_args_cannot_override_wrapper_safety(self):
        for blocked in ("-i", "-o", "--overwrite-input", "--reference-stream"):
            with self.subTest(blocked=blocked):
                with self.assertRaises(SystemExit):
                    sync.validate_engine_args([blocked])

    def test_explicit_vad_overrides_audio_default(self):
        command = sync.build_ffsubsync_command(
            ffsubsync="/bin/ffsubsync",
            video=Path("/movies/Movie.mkv"),
            subtitle=Path("/movies/Movie.pt-BR.srt"),
            output=Path("/movies/Movie.pt-BR_sync.srt"),
            reference="audio",
            offset=None,
            engine_args=["--vad=webrtc"],
        )

        self.assertIn("--vad=webrtc", command)
        self.assertNotIn("auditok", command)

    def test_try_harder_adds_recovery_args_without_overriding_user_args(self):
        args = type(
            "Args",
            (),
            {
                "engine_arg": [],
                "gss": False,
                "max_offset_seconds": 120,
                "no_fix_framerate": False,
                "try_harder": True,
                "vad": None,
            },
        )()

        engine_args = sync.collect_engine_args(args)

        self.assertEqual(engine_args.count("--max-offset-seconds"), 1)
        self.assertIn("120", engine_args)
        self.assertIn("--gss", engine_args)


if __name__ == "__main__":
    unittest.main()
