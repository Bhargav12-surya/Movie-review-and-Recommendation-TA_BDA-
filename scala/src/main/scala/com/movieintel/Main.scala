package com.movieintel

import com.movieintel.analytics.{MovieAnalytics, UserAnalytics}
import com.movieintel.cleaning.DataCleaning
import com.movieintel.config.{JobConfig, PathPolicy}
import com.movieintel.ingestion.MovieLensIngestion
import com.movieintel.io.{JsonCodec, PipelineIO}
import com.movieintel.streaming.ReviewStreamJob
import com.movieintel.transformations.{DataFrameTransformations, RddExamples}
import java.net.{InetAddress, ServerSocket}
import java.nio.file.{Files, Path}
import java.time.Instant
import java.util.UUID
import org.apache.spark.sql.SparkSession

/** Scala performs all batch/stream data work. No Python processes or network fetches. */
object Main {
  private def checkUiPort(): Unit = {
    val socket = new ServerSocket()
    try socket.bind(new java.net.InetSocketAddress(InetAddress.getByName("127.0.0.1"), 4040))
    finally socket.close()
  }

  private def inputMetadata(config: JobConfig): Seq[Map[String, Any]] =
    if (config.job == "smoke" || config.job == "stream") Seq.empty
    else Seq("ratings.csv", "movies.csv", "tags.csv", "links.csv").map { name =>
      val path = config.input.resolve(name)
      Map("file" -> name, "size_bytes" -> Files.size(path),
        "modified_at" -> Files.getLastModifiedTime(path).toString)
    }

  private def smoke(spark: SparkSession, config: JobConfig): Unit = {
    import spark.implicits._
    // Isolated, explicitly synthetic test evidence; never a catalogue or training source.
    val frame = Seq((1, "synthetic-A", 1.5), (2, "synthetic-B", 4.0))
      .toDF("fixture_id", "fixture_name", "fixture_value")
    val location = config.stage("smoke", "synthetic_roundtrip")
    PipelineIO.writeParquet(frame, location)
    val restored = spark.read.parquet(location)
    require(restored.count() == 2L, "Parquet round-trip row count mismatch.")
    require(restored.select("fixture_id").as[Int].rdd.reduce(_ + _) == 3,
      "Synthetic RDD round-trip mismatch.")
    PipelineIO.writeText(config.output.resolve("reports/smoke.json"),
      JsonCodec.encode(Map("synthetic_fixture" -> true, "parquet_roundtrip" -> "passed",
        "rdd_reduce" -> "passed", "rows" -> 2)) + "\n")
  }

  def execute(config: JobConfig): Unit = {
    config.validate()
    require(org.apache.spark.SPARK_VERSION == "4.3.0", "Matching Spark 4.3.0 is required.")
    require(scala.util.Properties.versionNumberString == "2.13.18",
      "Matching Scala 2.13.18 is required.")
    require(Runtime.version().feature() == 21, "Select the audited JDK 21 for this project.")
    checkUiPort()
    val before = inputMetadata(config)
    // The stream owns its output/checkpoint lifecycle and resume contract.
    if (config.job != "stream") PathPolicy.createNew(config.workspace, config.output)
    val eventLog = PathPolicy.createNew(config.workspace,
      config.workspace.resolve("artifacts/spark-events").resolve(UUID.randomUUID().toString))
    val started = Instant.now()
    val spark = SparkSession.builder().appName("MovieIntel-" + config.job)
      .master(config.master)
      .config("spark.driver.host", "127.0.0.1")
      .config("spark.driver.bindAddress", "127.0.0.1")
      .config("spark.ui.port", "4040")
      .config("spark.port.maxRetries", "0")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.shuffle.partitions", config.shufflePartitions.toString)
      .config("spark.sql.adaptive.enabled", "true")
      .config("spark.sql.csv.parser.columnPruning.enabled", "false")
      .config("spark.eventLog.enabled", "true")
      .config("spark.eventLog.dir", eventLog.toUri.toString)
      .getOrCreate()
    spark.conf.set("spark.movieintel.workspace", config.workspace.toString)
    spark.sparkContext.setLogLevel("WARN")
    var succeeded = false
    try {
      config.job match {
        case "smoke" => smoke(spark, config)
        case "stream" => ReviewStreamJob.run(spark, config)
        case "batch" | "rdd" =>
          val raw = MovieLensIngestion.run(spark, config)
          val clean = DataCleaning.run(spark, raw, config)
          if (config.job == "batch") {
            val features = DataFrameTransformations.run(spark, clean, config)
            PipelineIO.writeText(config.output.resolve("reports/movie_features_plan.txt"),
              features.movies.queryExecution.toString())
            MovieAnalytics.run(spark, clean, config)
            UserAnalytics.run(spark, clean, config)
          }
          RddExamples.run(spark, clean.tags, config)
      }
      require(before == inputMetadata(config), "Raw input metadata changed during execution.")
      succeeded = true
      if (config.holdUiSeconds > 0) {
        println("Spark UI: " + spark.sparkContext.uiWebUrl.getOrElse("unavailable"))
        // Explicit evaluator hold, bounded to one hour by JobConfig. Ctrl+C ends the run.
        Thread.sleep(config.holdUiSeconds.toLong * 1000L)
      }
    } finally {
      try {
        if (Files.isDirectory(config.output)) {
          val reportName = "execution-" + UUID.randomUUID().toString + ".json"
          PipelineIO.writeText(config.output.resolve("reports").resolve(reportName),
            JsonCodec.encode(Map("schema_version" -> 1, "job" -> config.job,
              "started_at" -> started.toString, "finished_at" -> Instant.now().toString,
              "status" -> (if (succeeded) "completed" else "failed"),
              "spark_version" -> spark.version, "scala_version" -> scala.util.Properties.versionNumberString,
              "java_version" -> System.getProperty("java.version"), "master" -> config.master,
              "spark_application_id" -> spark.sparkContext.applicationId,
              "ui_url" -> spark.sparkContext.uiWebUrl,
              "event_log_directory" -> config.workspace.relativize(eventLog).toString,
              "source_files" -> before, "synthetic_fixture" -> (config.job == "smoke"),
              "audience_score_implemented" -> false)) + "\n")
        }
      } finally spark.stop()
    }
  }

  def main(args: Array[String]): Unit = execute(JobConfig.parse(args))
}
