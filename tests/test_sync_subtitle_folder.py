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

    def test_subtitle_reference_mode_does_not_fall_back_to_audio(self):
        original_embedded = sync.find_embedded_english_subtitle
        original_external = sync.find_external_english_reference
        sync.find_embedded_english_subtitle = lambda video: None
        sync.find_external_english_reference = lambda folder, targets: None
        try:
            with self.assertRaises(SystemExit) as raised:
                sync.select_reference(
                    video=Path("movie.mkv"),
                    folder=Path("."),
                    subtitles=[Path("Movie.pt-BR.srt")],
                    mode="subtitle",
                )
            self.assertIn("--reference-mode audio", str(raised.exception))

            choice = sync.select_reference(
                video=Path("movie.mkv"),
                folder=Path("."),
                subtitles=[Path("Movie.pt-BR.srt")],
                mode="auto",
            )
            self.assertEqual(choice.value, "audio")
        finally:
            sync.find_embedded_english_subtitle = original_embedded
            sync.find_external_english_reference = original_external

    def test_embedded_english_reference_builds_ffsubsync_command(self):
        command = sync.build_ffsubsync_command(
            ffsubsync="/bin/ffsubsync",
            video=Path("/movies/Movie.mkv"),
            subtitle=Path("/movies/Movie.pt-BR.srt"),
            output=Path("/movies/Movie.pt-BR_sync.srt"),
            reference="embedded:s:0",
            offset=-1.2,
        )

        self.assertEqual(command[0], "/bin/ffsubsync")
        self.assertIn("--reference-stream", command)
        self.assertIn("s:0", command)
        self.assertIn("--apply-offset-seconds", command)
        self.assertIn("-1.2", command)


if __name__ == "__main__":
    unittest.main()
