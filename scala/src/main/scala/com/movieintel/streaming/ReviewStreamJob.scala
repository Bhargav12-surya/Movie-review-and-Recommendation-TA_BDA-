package com.movieintel.streaming

import com.movieintel.config.{JobConfig, PathPolicy, Schemas}
import com.movieintel.ingestion.ReviewIngestion
import com.movieintel.io.{JsonCodec, PipelineIO}
import java.io.StringWriter
import java.nio.channels.{FileChannel, FileLock}
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, StandardCopyOption, StandardOpenOption}
import java.time.Instant
import java.util.{Properties, UUID}
import scala.jdk.CollectionConverters._
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.Trigger
import org.apache.spark.storage.StorageLevel

final case class BatchResult(batchId: Long, replayed: Boolean, ledgerEvents: Long,
    currentReviews: Long, liveRealReviews: Long)

/** Bounded local demonstration sink. Each batch is a complete immutable snapshot.
  * Single writer + same-filesystem atomic publication + retained checkpoints.
  * No claim of production end-to-end exactly-once or a final audience score.
  */
object ReviewStreamJob {
  private val pipelineVersion = "review-stream-v1"
  private val maximumLedgerEvents = 100000L

  private def propertiesText(entries: Map[String, String]): String = {
    val properties = new Properties()
    entries.foreach { case (key, value) => properties.setProperty(key, value) }
    val writer = new StringWriter()
    properties.store(writer, "MovieIntel local stream metadata; no credentials")
    writer.toString
  }

  private def readProperties(path: Path): Map[String, String] = {
    require(Files.isRegularFile(path) && Files.size(path) <= 65536L, "Missing/oversized stream metadata.")
    val properties = new Properties()
    val reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)
    try properties.load(reader) finally reader.close()
    properties.stringPropertyNames().asScala.map(key => key -> properties.getProperty(key)).toMap
  }

  private def contract(config: JobConfig): Map[String, String] = Map(
    "pipeline_version" -> pipelineVersion,
    "event_input" -> PathPolicy.resolved(config.eventInput.get).toString,
    "checkpoint" -> PathPolicy.resolved(config.checkpoint.get).toString,
    "allow_synthetic" -> config.allowSyntheticEvents.toString,
    "late_reporting_interval" -> config.watermark,
    "maximum_ledger_events" -> maximumLedgerEvents.toString,
    "schema_version" -> "review-events-v1")

  private def committed(config: JobConfig): Seq[(Long, Path)] = {
    val directory = config.output.resolve("committed")
    if (!Files.exists(directory)) Seq.empty
    else {
      val stream = Files.list(directory)
      try {
        val paths = stream.iterator().asScala.take(10001).toVector
        require(paths.size <= 10000, "Demonstration snapshot limit reached; archive by reviewed procedure.")
        paths.filter(Files.isDirectory(_)).map { path =>
          val name = path.getFileName.toString
          require(name.matches("batch-[0-9]{20}"), "Unexpected committed snapshot name.")
          val id = name.stripPrefix("batch-").toLong
          val metadata = readProperties(path.resolve("commit.properties"))
          require(metadata.get("batch_id").contains(id.toString) &&
            metadata.get("pipeline_version").contains(pipelineVersion), "Invalid committed batch marker.")
          id -> path
        }.sortBy(_._1)
      } finally stream.close()
    }
  }

  private def withWriterLock[A](config: JobConfig)(body: => A): A = {
    val output = PathPolicy.output(config.workspace, config.output)
    require(Files.isDirectory(output), "Stream output must be initialized first.")
    val channel = FileChannel.open(output.resolve(".writer.lock"),
      StandardOpenOption.CREATE, StandardOpenOption.WRITE)
    var lock: FileLock = null
    try {
      lock = channel.tryLock()
      require(lock != null, "Another local stream writer owns this output.")
      body
    } finally {
      if (lock != null) lock.release()
      channel.close()
    }
  }

  /** Test/API entry; a same-ID replay uses the already committed checkpoint batch.
    * Inputs must be immutable. Do not manually reuse a batch ID for different data.
    */
  def processBatch(batch: DataFrame, batchId: Long, config: JobConfig): BatchResult =
    withWriterLock(config) { processBatchUnlocked(batch, batchId, config) }

  private def processBatchUnlocked(batch: DataFrame, batchId: Long, config: JobConfig): BatchResult = {
    require(batchId >= 0L, "Nonnegative checkpoint batch ID required.")
    val spark = batch.sparkSession
    spark.conf.set("spark.movieintel.workspace", config.workspace.toString)
    val output = PathPolicy.output(config.workspace, config.output)
    val previous = committed(config)
    previous.find(_._1 == batchId) match {
      case Some((_, path)) =>
        val metadata = readProperties(path.resolve("commit.properties"))
        return BatchResult(batchId, true, metadata("ledger_events").toLong,
          metadata("current_reviews").toLong, metadata("live_real_reviews").toLong)
      case None => ()
    }
    require(previous.lastOption.map(_._1 + 1L).getOrElse(0L) == batchId,
      "Checkpoint batch sequence does not match the immutable sink. Do not delete/reuse checkpoints.")
    val validated = ReviewIngestion.validate(batch, config.allowSyntheticEvents)
    val incoming = validated.accepted.drop("_corrupt_record")
    val all = previous.lastOption match {
      case Some((_, path)) => spark.read.parquet(path.resolve("ledger").toString)
        .unionByName(incoming)
      case None => incoming
    }
    // Only identical event ID+payload pairs collapse; conflicts are retained forever.
    val ledger = all.dropDuplicates("event_id", "payload_hash").persist(StorageLevel.MEMORY_AND_DISK)
    try {
      val ledgerCount = ledger.count()
      require(ledgerCount <= maximumLedgerEvents, "Local demonstration ledger event limit reached.")
      val badEventIds = ledger.groupBy("event_id").agg(countDistinct("payload_hash").as("versions"))
        .filter(col("versions") > 1).select("event_id")
      val badEventReviews = ledger.join(badEventIds, Seq("event_id"), "left_semi")
        .select("review_id").distinct().withColumn("reason", lit("conflicting_event_id"))
      val badRevisions = ledger.groupBy("review_id", "review_revision")
        .agg(countDistinct("semantic_hash").as("versions"))
        .filter(col("versions") > 1).select("review_id").distinct()
        .withColumn("reason", lit("conflicting_review_revision"))
      val badIdentities = ledger.groupBy("review_id").agg(
        countDistinct("movie_id").as("movies"), countDistinct("is_synthetic").as("source_kinds"))
        .filter(col("movies") > 1 || col("source_kinds") > 1).select("review_id")
        .withColumn("reason", lit("changed_review_identity"))
      val badReviews = badEventReviews.unionByName(badRevisions).unionByName(badIdentities)
        .groupBy("review_id").agg(concat_ws(";", sort_array(collect_set("reason"))).as("rejection_reason"))
      // A disputed review is withheld entirely; it does not revert to a favourable old revision.
      val eligibleLedger = ledger.join(badReviews.select("review_id"), Seq("review_id"), "left_anti")
      val rejectedConflicts = ledger.join(badReviews, Seq("review_id"), "inner")
      val current = eligibleLedger.withColumn("_order", row_number().over(Window.partitionBy("review_id")
        .orderBy(col("review_revision").desc, col("event_id").asc)))
        .filter(col("_order") === 1).drop("_order")
      val live = current.filter(col("operation") === "upsert" &&
        col("consent_eligible") && col("moderation_eligible"))
      val real = live.filter(!col("is_synthetic"))
      val analytics = real.groupBy("movie_id", "model_version").agg(
        count(lit(1)).as("eligible_review_count"),
        avg("positive_probability").as("mean_positive_probability"),
        avg("neutral_probability").as("mean_neutral_probability"),
        avg("negative_probability").as("mean_negative_probability"),
        avg(lit(100.0) * (col("positive_probability") + lit(0.5) * col("neutral_probability")))
          .as("unadjusted_review_index"), max("event_timestamp").as("last_analysis_event_time"))
        .withColumn("audience_sentiment_score", lit(null).cast("double"))
        .withColumn("score_message", lit("Not enough audience reviews yet."))
        .withColumn("method_version", lit(pipelineVersion))
      val staging = PathPolicy.createNew(config.workspace,
        output.resolve("staging").resolve("batch-" + batchId + "-" + UUID.randomUUID().toString))
      val datasets = Seq("ledger" -> ledger, "current_reviews" -> current,
        "active_reviews" -> live, "movie_analysis_inputs" -> analytics,
        "rejected_input" -> validated.rejected, "quarantined_history" -> rejectedConflicts)
      datasets.foreach { case (name, frame) => PipelineIO.writeParquet(frame, staging.resolve(name).toString) }
      val currentCount = current.count()
      val realCount = real.count()
      PipelineIO.writeText(staging.resolve("commit.properties"), propertiesText(Map(
        "pipeline_version" -> pipelineVersion, "batch_id" -> batchId.toString,
        "ledger_events" -> ledgerCount.toString, "current_reviews" -> currentCount.toString,
        "live_real_reviews" -> realCount.toString, "committed_at" -> Instant.now().toString)))
      val destination = PathPolicy.child(config.workspace, output,
        "committed/" + ("batch-%020d".format(batchId)))
      require(!Files.exists(destination), "Committed snapshot exists; overwrite forbidden.")
      Files.createDirectories(destination.getParent)
      // Both paths are checked under the same run root. No non-atomic fallback.
      Files.move(staging, destination, StandardCopyOption.ATOMIC_MOVE)
      BatchResult(batchId, false, ledgerCount, currentCount, realCount)
    } finally ledger.unpersist(blocking = false)
  }

  def run(spark: SparkSession, config: JobConfig): Unit = {
    require(config.job == "stream", "Streaming config required.")
    config.validate()
    val manifest = config.output.resolve("stream.properties")
    if (!config.resume) {
      PathPolicy.createNew(config.workspace, config.output)
      PathPolicy.createNew(config.workspace, config.checkpoint.get)
      PipelineIO.writeText(manifest, propertiesText(contract(config)))
    } else {
      require(Files.isDirectory(config.output) && Files.isDirectory(config.checkpoint.get),
        "Resume requires retained output and matching checkpoint directories.")
      require(readProperties(manifest) == contract(config), "Resume configuration differs from retained contract.")
      if (committed(config).nonEmpty) {
        require(Files.isDirectory(config.checkpoint.get.resolve("offsets")) &&
          Files.isRegularFile(config.checkpoint.get.resolve("metadata")),
          "Committed sink cannot resume with an empty/replaced Spark checkpoint.")
      }
    }
    withWriterLock(config) {
      val source = spark.readStream.schema(Schemas.ReviewEvents)
        .option("mode", "PERMISSIVE").option("columnNameOfCorruptRecord", "_corrupt_record")
        .option("maxFilesPerTrigger", config.maxFilesPerTrigger)
        .json(config.eventInput.get.toString)
      // All late revisions are accepted. No bounded-state watermark silently drops deletions.
      // The reporting interval is retained in the manifest, not claimed as a drop policy.
      val trigger = if (config.availableNow) Trigger.AvailableNow() else Trigger.ProcessingTime("5 seconds")
      val query = source.writeStream.queryName("movieintel_review_events")
        .option("checkpointLocation", config.checkpoint.get.toString)
        .foreachBatch((batch: DataFrame, id: Long) => { processBatchUnlocked(batch, id, config); () })
        .trigger(trigger).start()
      try query.awaitTermination() finally if (query.isActive) query.stop()
    }
  }
}
