"""Isolated synthetic file/manifest fixtures; no Spark installation or process."""
from __future__ import annotations

from contextlib import redirect_stdout
from importlib import util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = util.spec_from_file_location("spark_job_launcher", ROOT / "scripts/spark_job_launcher.py")
launcher = util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class SparkLauncherTests(unittest.TestCase):
    def setUp(self):
        self.owner = tempfile.TemporaryDirectory(prefix="movieintel-launcher-test-")
        self.addCleanup(self.owner.cleanup)
        self.root = Path(self.owner.name).resolve()
        config = json.loads((ROOT / "configs/environment.json").read_text(encoding="utf-8"))
        self.java = self.root / "tools/jdk"
        (self.java / "bin").mkdir(parents=True)
        (self.java / "bin" / ("java.exe" if os.name == "nt" else "java")).write_bytes(b"synthetic-file-only")
        (self.java / "release").write_text('JAVA_VERSION="21.0.12"\n', encoding="utf-8")
        config["java"]["home"] = str(self.java)
        (self.root / "configs/spark-local").mkdir(parents=True)
        (self.root / "configs/environment.json").write_text(json.dumps(config), encoding="utf-8")
        self.spark = self.root / "tools/spark"
        (self.spark / "bin").mkdir(parents=True)
        (self.spark / "bin" / ("spark-submit.cmd" if os.name == "nt" else "spark-submit")).write_bytes(b"synthetic")
        (self.spark / "jars").mkdir()
        for name in ("spark-core_2.13-4.3.0.jar", "spark-sql_2.13-4.3.0.jar", "spark-mllib_2.13-4.3.0.jar",
                     "scala-library-2.13.18.jar", "hadoop-client-api-3.5.0.jar", "hadoop-client-runtime-3.5.0.jar"):
            (self.spark / "jars" / name).touch()
        self.jar = self.root / "scala/target/scala-2.13/movieintel-spark_2.13-0.1.0.jar"
        self.jar.parent.mkdir(parents=True)
        self.make_jar()
        source = self.root / "data/raw/movielens/ml-32m"
        source.mkdir(parents=True)
        for name in ("ratings.csv", "movies.csv", "tags.csv", "links.csv"):
            (source / name).write_text("synthetic metadata fixture", encoding="utf-8")
        self.resources = {"disk": {"free_bytes": 30 * 1024**3},
                          "memory": {"status": "measured", "available_bytes": 6 * 1024**3}}

    def make_jar(self, spark="4.3.0", scala="2.13.18", main=True):
        with zipfile.ZipFile(self.jar, "w") as archive:
            archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nSpark-Version: " + spark +
                             "\nScala-Version: " + scala + "\n")
            if main:
                archive.writestr("com/movieintel/Main$.class", b"synthetic-metadata-only")

    def args(self, *extra):
        return launcher.parser().parse_args(["--workspace", str(self.root), "--spark-home", str(self.spark), *extra])

    def inspect(self, *extra):
        report = launcher.common.new_report("test", self.root)
        with patch.dict(os.environ, {}, clear=True), patch.object(launcher.common, "resource_snapshot", return_value=self.resources):
            command, environment = launcher.inspect(self.args(*extra), report)
        launcher.common.finalize(report)
        return report, command, environment

    def test_metadata_preflight_has_no_execution_command(self):
        report, command, _ = self.inspect()
        self.assertTrue(report["ready"])
        self.assertEqual(command, [])
        self.assertFalse(report["executed"])

    def test_project_config_spark_home_is_used_without_path_or_environment(self):
        path = self.root / "configs/environment.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        config["spark"]["home"] = str(self.spark)
        path.write_text(json.dumps(config), encoding="utf-8")
        args = launcher.parser().parse_args(["--workspace", str(self.root), "--job", "preflight"])
        report = launcher.common.new_report("synthetic-config-discovery-test", self.root)
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(launcher.common, "resource_snapshot", return_value=self.resources), \
                patch.object(launcher, "execute_command", side_effect=AssertionError("No process permitted")):
            command, environment = launcher.inspect(args, report)
        self.assertEqual(report["selected_spark_home"], str(self.spark))
        self.assertEqual(environment["SPARK_HOME"], str(self.spark))
        self.assertEqual(command, [])

    def test_dry_run_builds_bounded_local_command_without_outputs(self):
        report, command, _ = self.inspect("--job", "batch", "--output", "data/processed/new", "--dry-run")
        self.assertTrue(report["ready"])
        self.assertIn("local[2]", command)
        self.assertNotIn("--packages", command)
        self.assertNotIn("sbt", command)
        self.assertFalse((self.root / "data/processed").exists())

    def test_dry_run_main_never_starts_process(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(launcher.common, "resource_snapshot", return_value=self.resources), \
                patch.object(launcher, "execute_command", side_effect=AssertionError("No process allowed")), redirect_stdout(out):
            code = launcher.main(["--workspace", str(self.root), "--spark-home", str(self.spark), "--job", "smoke",
                                  "--output", "artifacts/smoke", "--dry-run", "--json"])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out.getvalue())["executed"])
        self.assertFalse((self.root / "artifacts").exists())

    def test_wrong_jar_version_is_blocked(self):
        self.make_jar(spark="3.5.0")
        report, _, _ = self.inspect()
        self.assertIn("project.jar", report["blocking_checks"])

    def test_jar_without_entry_point_is_blocked(self):
        self.make_jar(main=False)
        self.assertIn("project.jar", self.inspect()[0]["blocking_checks"])

    def test_missing_distribution_is_blocked_without_resolver(self):
        (self.spark / "jars/spark-sql_2.13-4.3.0.jar").unlink()
        self.assertIn("spark.distribution", self.inspect()[0]["blocking_checks"])

    def test_raw_legacy_escape_and_dependency_outputs_refused(self):
        for value in ("data/raw/new", "temp/new", "../outside", ".git/new", "x/NODE_MODULES/new"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.inspect("--job", "smoke", "--output", value)

    def test_shell_expansion_arguments_refused(self):
        for value in ("test&whoami", "%SECRET%", "bang!", "new\nline", 'quote"'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                launcher.shell_safe(value)

    def test_existing_output_refused(self):
        (self.root / "artifacts/existing").mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.inspect("--job", "smoke", "--output", "artifacts/existing")

    def test_resources_block_insufficient_ram_and_reserve(self):
        self.resources["memory"]["available_bytes"] = 3 * 1024**3
        self.resources["disk"]["free_bytes"] = 19 * 1024**3
        blocked = self.inspect()[0]["blocking_checks"]
        self.assertIn("resources.ram", blocked)
        self.assertIn("resources.disk", blocked)

    def test_local_master_and_partition_bounds(self):
        for pair in (("--master", "local[*]"), ("--master", "spark://remote"), ("--shuffle-partitions", "129")):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                self.inspect(*pair)

    def test_stream_requires_separate_explicit_paths(self):
        (self.root / "data/events/input").mkdir(parents=True)
        base = ("--job", "stream", "--event-input", "data/events/input", "--output", "data/processed/stream")
        with self.assertRaises(ValueError):
            self.inspect(*base)
        with self.assertRaises(ValueError):
            self.inspect(*base, "--checkpoint", "data/processed/stream/cp")
        report, command, _ = self.inspect(*base, "--checkpoint", "data/checkpoints/stream",
                                          "--continuous", "--max-files-per-trigger", "2")
        self.assertTrue(report["ready"])
        self.assertIn("--continuous", command)
        self.assertIn("24 hours", command)

    def test_resume_requires_retained_output_and_checkpoint(self):
        (self.root / "data/events/input").mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.inspect("--job", "stream", "--event-input", "data/events/input", "--output", "data/processed/stream",
                         "--checkpoint", "data/checkpoints/stream", "--resume")

    def test_child_environment_does_not_change_parent(self):
        with patch.dict(os.environ, {"JAVA_HOME": "original", "SPARK_SUBMIT_OPTS": "private-agent"}, clear=True):
            result = launcher.child_environment(self.java, self.spark, self.root)
            self.assertEqual(os.environ["JAVA_HOME"], "original")
            self.assertEqual(result["JAVA_HOME"], str(self.java))
            self.assertEqual(result["SPARK_LOCAL_IP"], "127.0.0.1")
            self.assertNotIn("SPARK_SUBMIT_OPTS", result)

    def test_jvm_options_blocked_without_logging_values(self):
        report = launcher.common.new_report("test", self.root)
        with patch.dict(os.environ, {"JAVA_TOOL_OPTIONS": "secret-test-value"}, clear=True):
            launcher.runtime_checks(report, json.loads((self.root / "configs/environment.json").read_text()),
                                    self.java, self.spark, self.jar)
        launcher.common.finalize(report)
        self.assertIn("runtime.unreviewed_options", report["blocking_checks"])
        self.assertNotIn("secret-test-value", json.dumps(report))

    def test_project_resolver_defaults_blocked(self):
        (self.root / "configs/spark-local/spark-defaults.conf").write_text(
            "spark.jars.packages private:package:1.0\n", encoding="utf-8")
        report = self.inspect()[0]
        self.assertIn("runtime.unreviewed_options", report["blocking_checks"])
        self.assertNotIn("private:package", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
