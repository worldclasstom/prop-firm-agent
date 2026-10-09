"""The release workflow derives tags from the package version; a mismatch must fail."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'release_tag.py'
spec = importlib.util.spec_from_file_location('release_tag', SCRIPT)
release_tag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_tag)


class ReleaseTagTests(unittest.TestCase):
    def test_version_forms(self):
        self.assertEqual(release_tag.tag_for('0.2.0b9'), ('v0.2.0-beta.9', True))
        self.assertEqual(release_tag.tag_for('0.2.0a1'), ('v0.2.0-alpha.1', True))
        self.assertEqual(release_tag.tag_for('1.0.0rc2'), ('v1.0.0-rc.2', True))
        self.assertEqual(release_tag.tag_for('1.0.0'), ('v1.0.0', False))
        for bad in ('0.2', '0.2.0.dev1', 'v0.2.0', '0.2.0-beta.9'):
            with self.assertRaises(ValueError):
                release_tag.tag_for(bad)

    def test_repository_version_matches_both_files(self):
        root = Path(__file__).resolve().parents[1]
        from propfirm import __version__
        self.assertEqual(release_tag.repository_version(root), __version__)

    def test_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'propfirm').mkdir()
            (root / 'pyproject.toml').write_text('[project]\nname = "x"\nversion = "0.3.0b1"\n')
            (root / 'propfirm' / '__init__.py').write_text('__version__ = "0.2.0b9"\n')
            with self.assertRaises(ValueError):
                release_tag.repository_version(root)


if __name__ == '__main__':
    unittest.main()
