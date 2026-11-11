package com.movieintel.harness

import com.movieintel.config.{JobConfig, Schemas}
import com.movieintel.io.JsonCodec
import com.movieintel.streaming.ReviewStreamJob
import java.io.File
import java.nio.channels.FileChannel
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths, StandardCopyOption, StandardOpenOption}
import java.security.MessageDigest
import java.time.Instant
import java.util.UUID
import java.util.concurrent.TimeUnit
import org.apache.spark.sql.{Row, SparkSession}
import org.apache.spark.sql.functions._
import scala.collection.mutable.ArrayBuffer
import scala.jdk.CollectionConverters._
import scala.util.control.NonFatal

/** A separate JVM holds the exact OS file lock used by the real stream writer. */
object RecoveryLockHolder {
  def main(args: Array[String]): Unit = {
    require(args.length == 4, "lock, ready, release and fixture-root paths required.")
    val root = Paths.get(args(3)).toRealPath()
    val paths = args.take(3).map(value => Paths.get(value).toAbsolutePath.normalize())
    require(paths.forall(p => p != root && p.startsWith(root)), "Lock paths must stay in fixture.")
    val channel = FileChannel.open(paths(0), StandardOpenOption.CREATE, StandardOpenOption.WRITE)
    val lock = channel.tryLock()
    require(lock != null, "Another process already holds this test lock.")
    try {
      Files.writeString(paths(1), "locked\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW)
      val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(60)
      while (!Files.exists(paths(2)) && System.nanoTime() < deadline) Thread.sleep(25)
      require(Files.exists(paths(2)), "Test lock release timed out.")
    } finally {
      lock.release()
      channel.close()
    }
  }
}

/** Isolated synthetic checks; no production data, model training, or deletion.
  * Abandoned staging is deliberately constructed, not a forced process-crash test.
  */
object StreamingRecoveryRunner {
  def main(args: Array[String]): Unit = {
    require(args.length == 3, "fixture-root, runner-jar and scala-library paths required.")
    val root = Paths.get(args(0)).toRealPath()
    require(root.getFileName.toString.matches("stream-recovery-[0-9a-f]{32}"),
      "Use the newly generated isolated fixture root.")
    val runnerJar = Paths.get(args(1)).toRealPath()
    val scalaLibrary = Paths.get(args(2)).toRealPath()
    val checks = ArrayBuffer.empty[Map[String, Any]]
    var failure: Option[Throwable] = None

    def check(name: String, passed: Boolean): Unit = {
      checks += Map("check" -> name, "passed" -> passed)
      println((if (passed) "PASS: " else "FAIL: ") + name)
      require(passed, "Recovery assertion failed: " + name)
    }

    def digest(path: Path): String = MessageDigest.getInstance("SHA-256")
      .digest(Files.readAllBytes(path)).map(b => "%02x".format(b & 0xff)).mkString

    def fingerprint(directory: Path): Map[String, String] = {
      val entries = Files.walk(directory)
      try entries.iterator().asScala.filter(Files.isRegularFile(_))
        .map(p => directory.relativize(p).toString -> digest(p)).toMap
      finally entries.close()
    }

    // Moves occur only inside this new test root. Existing project artifacts are never targets.
    def fixtureMove(source: Path, target: Path): Unit = {
      val from = source.toRealPath()
      val to = target.toAbsolutePath.normalize()
      require(from != root && from.startsWith(root) && to != root && to.startsWith(root),
        "Both move paths must remain below the generated fixture.")
      require(to.getParent.toRealPath().startsWith(root) && !Files.exists(to),
        "Move target must have a safe existing parent and must not exist.")
      Files.move(from, to, StandardCopyOption.ATOMIC_MOVE)
      ()
    }

    def event(revision: Long): Map[String, Any] = Map(
      "event_id" -> s"synthetic-recovery-event-$revision",
      "review_id" -> "synthetic-recovery-review", "review_revision" -> revision,
      "movie_id" -> "synthetic-recovery-movie", "operation" -> "upsert",
      "event_time" -> "2026-01-01T00:00:00Z",
      "positive_probability" -> 0.7, "neutral_probability" -> 0.2,
      "negative_probability" -> 0.1, "model_version" -> "synthetic-test-only",
      "canonical_movie_validated" -> true, "consent_eligible" -> true,
      "moderation_eligible" -> true, "is_synthetic" -> true)

    def publish(events: Path, revision: Long): Unit = {
      val partial = events.resolve(".pending-" + UUID.randomUUID().toString)
      Files.writeString(partial, JsonCodec.encode(event(revision)) + "\n",
        StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW)
      fixtureMove(partial, events.resolve("synthetic-" + UUID.randomUUID().toString + ".jsonl"))
    }

    val spark = SparkSession.builder().master("local[1]").appName("Synthetic stream recovery checks")
      .config("spark.ui.enabled", "false").config("spark.driver.host", "127.0.0.1")
      .config("spark.driver.bindAddress", "127.0.0.1")
      .config("spark.sql.session.timeZone", "UTC").config("spark.sql.shuffle.partitions", "2")
      .config("spark.movieintel.workspace", root.toString).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    def frame(revision: Long) = {
      val row = Row(s"synthetic-recovery-event-$revision", "synthetic-recovery-review", revision,
        "synthetic-recovery-movie", "upsert", "2026-01-01T00:00:00Z",
        0.7, 0.2, 0.1, "synthetic-test-only", true, true, true, true, null)
      spark.createDataFrame(spark.sparkContext.parallelize(Seq(row), 1), Schemas.ReviewEvents)
    }

    try {
      // The child holds an OS lock in a different JVM; the real processBatch must refuse it.
      val writer = Files.createDirectories(root.resolve("writer"))
      val writerOutput = Files.createDirectory(writer.resolve("output"))
      val writerConfig = JobConfig(root, root.resolve("unused"), writerOutput, job = "stream",
        allowSyntheticEvents = true)
      val lockPath = writerOutput.resolve(".writer.lock")
      val ready = writer.resolve("holder-ready.txt")
      val release = writer.resolve("holder-release.txt")
      val java = Paths.get(System.getProperty("java.home"), "bin",
        if (System.getProperty("os.name").startsWith("Windows")) "java.exe" else "java")
      val child = new ProcessBuilder(java.toString, "-Xmx64m", "-cp",
        runnerJar.toString + File.pathSeparator + scalaLibrary.toString,
        "com.movieintel.harness.RecoveryLockHolder", lockPath.toString, ready.toString,
        release.toString, root.toString).redirectErrorStream(true)
        .redirectOutput(writer.resolve("lock-holder.log").toFile).start()
      try {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(20)
        while (!Files.exists(ready) && child.isAlive && System.nanoTime() < deadline) Thread.sleep(25)
        check("separate JVM acquired writer lock", Files.exists(ready) && child.isAlive)
        var refused = false
        try ReviewStreamJob.processBatch(frame(1L), 0L, writerConfig)
        catch { case e: IllegalArgumentException if e.getMessage.contains("Another local stream writer") => refused = true }
        check("competing stream writer rejected", refused)
        check("blocked writer did not commit", !Files.exists(writerOutput.resolve("committed")))
      } finally {
        if (child.isAlive) {
          Files.writeString(release, "release\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW)
          if (!child.waitFor(10L, TimeUnit.SECONDS)) {
            child.destroyForcibly()
            child.waitFor(5L, TimeUnit.SECONDS)
          }
        }
      }
      check("lock holder exited cleanly", !child.isAlive && child.exitValue() == 0)
      val unlocked = ReviewStreamJob.processBatch(frame(1L), 0L, writerConfig)
      check("writer proceeds after lock release",
        unlocked.ledgerEvents == 1L && unlocked.currentReviews == 1L && unlocked.liveRealReviews == 0L)

      val streamRoot = Files.createDirectory(root.resolve("checkpoint-recovery"))
      val events = Files.createDirectory(streamRoot.resolve("events"))
      val output = streamRoot.resolve("output")
      val checkpoint = streamRoot.resolve("checkpoint")
      val config = JobConfig(root, root.resolve("unused"), output, job = "stream", master = "local[1]",
        shufflePartitions = 2, allowSyntheticEvents = true,
        eventInput = Some(events), checkpoint = Some(checkpoint))
      publish(events, 1L)
      ReviewStreamJob.run(spark, config)
      val originalBatch = output.resolve("committed/batch-00000000000000000000")
      check("real file stream initialized checkpoint",
        Files.isRegularFile(checkpoint.resolve("metadata")) && Files.isRegularFile(checkpoint.resolve("commits/0")))
      val originalData = fingerprint(originalBatch)
      val originalCheckpoint = fingerprint(checkpoint)

      // Retain the original checkpoint intact, substituting an empty directory only in this fixture.
      val backup = streamRoot.resolve("checkpoint-original-retained")
      fixtureMove(checkpoint, backup)
      Files.createDirectory(checkpoint)
      var missingRefused = false
      try ReviewStreamJob.run(spark, config.copy(resume = true))
      catch { case e: IllegalArgumentException if e.getMessage.contains("empty/replaced Spark checkpoint") =>
        missingRefused = true }
      check("empty replacement checkpoint rejected", missingRefused)
      check("checkpoint rejection preserves committed batch", fingerprint(originalBatch) == originalData)
      check("original checkpoint retained unchanged", fingerprint(backup) == originalCheckpoint)
      fixtureMove(checkpoint, streamRoot.resolve("checkpoint-empty-retained"))
      fixtureMove(backup, checkpoint)
      check("original checkpoint restored exactly", fingerprint(checkpoint) == originalCheckpoint)
      ReviewStreamJob.run(spark, config.copy(resume = true))
      check("restored checkpoint resumes without rewriting batch", fingerprint(originalBatch) == originalData)

      // Simulate an abandoned incomplete write. No committed marker is manufactured.
      val abandoned = Files.createDirectory(output.resolve("staging").resolve("abandoned-synthetic-write"))
      spark.range(1).withColumn("synthetic_fixture", lit(true)).write.mode("errorifexists")
        .parquet(abandoned.resolve("partial_ledger").toString)
      val abandonedData = fingerprint(abandoned)
      check("incomplete staging has no commit marker", !Files.exists(abandoned.resolve("commit.properties")))
      publish(events, 2L)
      ReviewStreamJob.run(spark, config.copy(resume = true))
      val second = output.resolve("committed/batch-00000000000000000001")
      val current = spark.read.parquet(second.resolve("current_reviews").toString)
      check("next revision commits despite abandoned staging",
        current.count() == 1L && current.head().getAs[Long]("review_revision") == 2L &&
          current.head().getAs[Boolean]("is_synthetic"))
      check("event ledger has no lost or duplicate events",
        spark.read.parquet(second.resolve("ledger").toString).count() == 2L)
      check("synthetic events excluded from audience evidence",
        spark.read.parquet(second.resolve("movie_analysis_inputs").toString).count() == 0L)
      check("abandoned staging preserved without promotion", fingerprint(abandoned) == abandonedData)
      check("earlier committed batch unchanged", fingerprint(originalBatch) == originalData)
      val allCommitted = fingerprint(output.resolve("committed"))
      ReviewStreamJob.run(spark, config.copy(resume = true))
      check("final restart preserves all committed snapshots", fingerprint(output.resolve("committed")) == allCommitted)
    } catch {
      case NonFatal(error) => failure = Some(error)
    } finally {
      val passed = failure.isEmpty && checks.nonEmpty && checks.forall(_("passed") == true)
      val report = Map("schema_version" -> 1, "passed" -> passed, "synthetic_fixture" -> true,
        "generated_at" -> Instant.now().toString, "checks" -> checks.toVector,
        "error_type" -> failure.map(_.getClass.getName), "error_message" -> failure.map(_.getMessage),
        "spark_version" -> spark.version, "scala_version" -> scala.util.Properties.versionNumberString,
        "limitations" -> Seq("Abandoned staging was simulated; no Spark process was forcibly crashed.",
          "Standalone integration assertions do not execute the ScalaTest/SBT suite.",
          "No end-to-end exactly-once or privacy-deletion guarantee is established."))
      try Files.writeString(root.resolve("recovery_report.json"), JsonCodec.encode(report) + "\n",
        StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW)
      finally spark.stop()
    }
    failure.foreach(throw _)
  }
}

