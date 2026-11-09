"""Generated metadata-discovery contracts; no build/service/model execution.

All jar/launcher files in these tests are explicitly synthetic file fixtures.
The tests are intended for the user's later validation run.
"""
from __future__ import annotations

from importlib import util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def owned_module(name):
    spec = util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


discovery = owned_module("_toolchain_discovery")
verifier = owned_module("verify_environment")


class ToolchainDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.owner = tempfile.TemporaryDirectory(prefix="movieintel-toolchain-test-")
        self.addCleanup(self.owner.cleanup)
        self.root = Path(self.owner.name).resolve()
        self.spark = self.root / "tools/spark"
        self.sbt = self.root / "tools/sbt"
        self.expected = {"version": "4.3.0", "scala_version": "2.13.18", "hadoop_version": "3.5.0"}

    def prepare_spark(self, release="Spark 4.3.0 (synthetic) built for Hadoop 3.5.0\n"):
        (self.spark / "bin").mkdir(parents=True)
        (self.spark / "jars").mkdir()
        for binary in ("spark-submit.cmd", "spark-shell.cmd") if os.name == "nt" else ("spark-submit", "spark-shell"):
            (self.spark / "bin" / binary).write_text("synthetic metadata fixture", encoding="utf-8")
        for name in ("spark-core_2.13-4.3.0.jar", "spark-sql_2.13-4.3.0.jar", "spark-mllib_2.13-4.3.0.jar",
                     "scala-library-2.13.18.jar", "hadoop-client-api-3.5.0.jar", "hadoop-client-runtime-3.5.0.jar"):
            (self.spark / "jars" / name).touch()
        if release is not None:
            (self.spark / "RELEASE").write_text(release, encoding="utf-8")

    def prepare_sbt(self, version="1.10.7"):
        (self.sbt / "bin").mkdir(parents=True)
        binary = "sbt.bat" if os.name == "nt" else "sbt"
        prefix = "set " if os.name == "nt" else ""
        (self.sbt / "bin" / binary).write_text(prefix + "init_sbt_version=" + version + "\n", encoding="utf-8")
        (self.sbt / "bin/sbt-launch.jar").write_bytes(b"synthetic metadata only")

    def test_home_precedence_and_relative_configuration(self):
        self.assertEqual(discovery.selected_home(self.root, "explicit", "environment", "configured"),
                         self.root / "explicit")
        self.assertEqual(discovery.selected_home(self.root, environment="environment", configured="configured"),
                         self.root / "environment")
        self.assertEqual(discovery.selected_home(self.root, configured="tools/spark"), self.spark)
        self.assertIsNone(discovery.selected_home(self.root))

    def test_missing_explicit_home_never_silently_selects_another_installation(self):
        self.prepare_spark()
        chosen = discovery.selected_home(self.root, explicit="missing", configured=str(self.spark))
        self.assertEqual(chosen, self.root / "missing")
        self.assertEqual(discovery.spark_metadata(chosen, self.expected)["status"], "missing")

    def test_exact_release_and_jar_names_are_metadata_only_evidence(self):
        self.prepare_spark()
        result = discovery.spark_metadata(self.spark, self.expected)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["version"], "4.3.0")
        self.assertFalse(result["runtime_executed"])
        self.assertTrue(result["metadata_only"])

    def test_wrong_release_cannot_pass_from_matching_filenames(self):
        self.prepare_spark("Spark 4.2.0 (synthetic) built for Hadoop 3.5.0\n")
        self.assertEqual(discovery.spark_metadata(self.spark, self.expected)["status"], "fail")

    def test_missing_release_remains_unverified(self):
        self.prepare_spark(None)
        self.assertEqual(discovery.spark_metadata(self.spark, self.expected)["status"], "unverified")

    def test_missing_jar_is_reported_without_resolution(self):
        self.prepare_spark()
        missing = self.spark / "jars/spark-mllib_2.13-4.3.0.jar"
        missing.unlink()
        result = discovery.spark_metadata(self.spark, self.expected)
        self.assertEqual(result["status"], "missing")
        self.assertIn(missing.name, result["missing_jars"])

    def test_sbt_default_version_does_not_claim_bootstrap_or_build_execution(self):
        self.prepare_sbt()
        result = discovery.sbt_metadata(self.sbt, "1.10.7")
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["launcher_default_version"], "1.10.7")
        self.assertFalse(result["bootstrap_verified"])
        self.assertFalse(result["runtime_executed"])
        self.assertEqual(discovery.sbt_metadata(self.sbt, "1.11.0")["status"], "fail")

    def test_environment_verifier_finds_configured_tools_without_path_or_processes(self):
        self.prepare_spark()
        self.prepare_sbt()
        config = {"spark": {**self.expected, "home": str(self.spark)},
                  "sbt": {"version": "1.10.7", "home": str(self.sbt)}}
        report = verifier.common.new_report("synthetic-discovery-test", self.root)
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(verifier.common, "executable", return_value=None), \
                patch.object(verifier.common, "run_program", side_effect=AssertionError("No runtime permitted")):
            verifier.inspect_jvm_toolchain(self.root, config, report, required=True)
        checks = {item["id"]: item for item in report["checks"]}
        self.assertEqual(checks["tool.sbt"]["status"], "pass")
        self.assertEqual(checks["tool.spark-submit"]["status"], "pass")
        self.assertTrue(checks["tool.spark-submit"]["evidence"]["metadata_only"])


if __name__ == "__main__":
    unittest.main()
