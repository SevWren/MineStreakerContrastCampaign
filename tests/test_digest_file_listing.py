import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from list_unignored_files import collect_files, collect_git_tracked_and_unignored_files


class DigestFileListingTests(unittest.TestCase):
    def test_fallback_collection_outside_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.txt").write_text("x", encoding="utf-8")
            (root / "results").mkdir()
            (root / "results" / "ignore.png").write_text("x", encoding="utf-8")
            files = collect_git_tracked_and_unignored_files(root)
            self.assertEqual(files, [Path("keep.txt")])

    def test_git_native_collection_returns_sorted_results(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git not available")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run([git, "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run([git, "config", "user.email", "codex@example.com"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run([git, "config", "user.name", "Codex"], cwd=root, check=True, capture_output=True, text=True)
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "b.txt").write_text("b", encoding="utf-8")
            subprocess.run([git, "add", "a.txt"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run([git, "commit", "-m", "init"], cwd=root, check=True, capture_output=True, text=True)
            files = collect_git_tracked_and_unignored_files(root)
            self.assertEqual(files, [Path("a.txt"), Path("b.txt")])

    def test_collect_files_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "x.txt").write_text("x", encoding="utf-8")
            self.assertEqual(collect_files(root), [Path("x.txt")])


if __name__ == "__main__":
    unittest.main()
