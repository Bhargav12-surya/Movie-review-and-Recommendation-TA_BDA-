"""Filename-only cache diagnostics with isolated files; no resolver execution."""
from importlib import util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = util.spec_from_file_location("verify_spark_cache", ROOT / "scripts/verify_spark_cache.py")
cache = util.module_from_spec(spec)
spec.loader.exec_module(cache)


class CacheInspectionTests(unittest.TestCase):
    def test_missing_cache_never_claims_a_complete_classpath(self):
        with tempfile.TemporaryDirectory(prefix="movieintel-cache-test-") as folder:
            report = cache.inspect(Path(folder) / "missing", "2.13.18", "4.3.0", "1.10.7")
            self.assertFalse(report["cache_root_exists"])
            self.assertFalse(report["complete_classpath_verified"])
            self.assertEqual(report["files_examined"], 0)

    def test_exact_versions_match_and_other_versions_do_not(self):
        with tempfile.TemporaryDirectory(prefix="movieintel-cache-test-") as folder:
            root = Path(folder)
            (root / "scala-compiler-2.13.18.jar").write_bytes(b"synthetic metadata fixture")
            (root / "spark-core_2.13-3.5.0.jar").touch()
            report = cache.inspect(root, "2.13.18", "4.3.0", "1.10.7")
            self.assertEqual(len(report["matching_files"]["scala-compiler-2.13.18.jar"]), 1)
            self.assertEqual(report["matching_files"]["spark-core_2.13-4.3.0.jar"], [])
            self.assertFalse(report["resolver_invoked"])
            self.assertEqual((root / "scala-compiler-2.13.18.jar").read_bytes(), b"synthetic metadata fixture")

    def test_scan_limit_is_explicit_and_not_a_complete_absence_claim(self):
        with tempfile.TemporaryDirectory(prefix="movieintel-cache-test-") as folder:
            root = Path(folder)
            for index in range(5):
                (root / (str(index) + ".jar")).touch()
            report = cache.inspect(root, "2.13.18", "4.3.0", "1.10.7", limit=2)
            self.assertEqual(report["files_examined"], 2)
            self.assertTrue(report["scan_capped"])


if __name__ == "__main__":
    unittest.main()
