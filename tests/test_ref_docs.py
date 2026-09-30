import tempfile
import unittest
from pathlib import Path

from ref_docs import (
    discover_batches,
    latest_batches,
    main,
    normalized_source,
    render_bundle,
)


def write_pair(
    folder: Path, label: str, *, completed: bool = True
) -> tuple[Path, Path]:
    folder.mkdir(parents=True)
    subtitle = folder / f"{label}_chus字幕(確定).txt"
    super_file = folder / f"{label}_super(確定).txt"
    subtitle.write_text(f"{label} subtitle\n", encoding="utf-8")
    super_file.write_text(f"{label} super\n", encoding="utf-8")
    if completed:
        output = folder / "output"
        output.mkdir()
        (output / f"{label}_字幕_final.docx").write_bytes(b"subtitle")
        (output / f"{label}_super_final.docx").write_bytes(b"super")
    return subtitle, super_file


class ReferenceDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_latest_batches_select_latest_complete_numbered_folders(self) -> None:
        write_pair(self.root / "doc-2", "second")
        write_pair(self.root / "doc-10", "tenth")
        incomplete = self.root / "doc-11"
        incomplete.mkdir()
        (incomplete / "eleventh_chus字幕.txt").write_text(
            "incomplete", encoding="utf-8"
        )
        (self.root / "misc").mkdir()

        batches = latest_batches(discover_batches(self.root), limit=1)

        self.assertEqual([batch.folder.name for batch in batches], ["doc-10"])

    def test_source_pair_without_both_final_documents_is_incomplete(self) -> None:
        write_pair(self.root / "doc-1", "finished")
        write_pair(self.root / "doc-2", "current", completed=False)

        batches = discover_batches(self.root)

        self.assertEqual([batch.folder.name for batch in batches], ["doc-1"])

    def test_discovery_ignores_nonworking_files(self) -> None:
        subtitle, super_file = write_pair(self.root / "doc-1", "episode")
        (self.root / "doc-1/episode_chus字幕(確定).baseline.txt").write_text(
            "baseline", encoding="utf-8"
        )
        (self.root / "doc-1/~episode_super(確定).txt").write_text(
            "temporary", encoding="utf-8"
        )
        (self.root / "doc-1/episode_super(確定).txt:Zone.Identifier").write_text(
            "metadata", encoding="utf-8"
        )

        batches = discover_batches(self.root)

        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].subtitle, subtitle)
        self.assertEqual(batches[0].super_file, super_file)

    def test_render_bundle_includes_both_source_files(self) -> None:
        subtitle, super_file = write_pair(self.root / "doc-3", "episode")
        batch = discover_batches(self.root)[0]

        rendered = render_bundle(self.root, [batch])

        self.assertIn("# Latest 1 Document References", rendered)
        self.assertIn(f"Filename: `{subtitle.relative_to(self.root)}`", rendered)
        self.assertIn("episode subtitle", rendered)
        self.assertIn(f"Filename: `{super_file.relative_to(self.root)}`", rendered)
        self.assertIn("episode super", rendered)

    def test_source_reader_supports_utf16_files(self) -> None:
        source = self.root / "episode_chus字幕.txt"
        source.write_text("中文字幕\n", encoding="utf-16")

        self.assertEqual(normalized_source(source), "中文字幕")

    def test_source_reader_normalizes_windows_line_endings(self) -> None:
        source = self.root / "episode_super.txt"
        source.write_bytes(b"first\r\nsecond\r\n")

        self.assertEqual(normalized_source(source), "first\nsecond")

    def test_main_writes_latest_four_reference_file(self) -> None:
        for number in range(1, 6):
            write_pair(self.root / f"doc-{number}", f"episode-{number}")

        self.assertEqual(main(["--root", str(self.root)]), 0)

        output = self.root / "refs/latest-4-docs.md"
        self.assertTrue(output.is_file())
        content = output.read_text(encoding="utf-8")
        self.assertNotIn("# doc-1", content)
        self.assertIn("# doc-2", content)
        self.assertIn("# doc-5", content)


if __name__ == "__main__":
    unittest.main()
