package com.movieintel

import com.movieintel.config.{JobConfig, Schemas}
import com.movieintel.ingestion.ReviewIngestion
import com.movieintel.streaming.ReviewStreamJob
import java.nio.file.{Files, Path}
import java.util.UUID
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions._
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

/** Synthetic probabilities test calculations only. They are never real predictions.
  * Requires manually prepared Spark + ScalaTest; not executed by parser-only checks.
  */
class ReviewStreamSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var root: Path = _
  private var spark: SparkSession = _

  override def beforeAll(): Unit = {
    super.beforeAll()
    root = Files.createTempDirectory("movieintel-stream-test-").toRealPath()
    spark = SparkSession.builder().master("local[1]").appName("Synthetic streaming contracts")
      .config("spark.ui.enabled", "false").config("spark.driver.host", "127.0.0.1")
      .config("spark.driver.bindAddress", "127.0.0.1")
      .config("spark.sql.session.timeZone", "UTC").config("spark.sql.shuffle.partitions", "2")
      .config("spark.movieintel.workspace", root.toString).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
  }
  override def afterAll(): Unit = {
    try { if (spark != null) spark.stop() } finally super.afterAll()
    // Retain the isolated test tree for failed snapshot inspection; no user data cleanup.
  }

  private def event(id: String, review: String = "review-1", revision: Long = 1L,
      movie: String = "canonical-fixture-1", operation: String = "upsert",
      positive: java.lang.Double = 0.7, neutral: java.lang.Double = 0.2,
      negative: java.lang.Double = 0.1, consent: Boolean = true, moderation: Boolean = true,
      synthetic: Boolean = false, model: String = "synthetic-test-model-v1"): Row = Row(
    id, review, revision, movie, operation, "2026-01-01T00:00:00Z", positive, neutral,
    negative, model, true, consent, moderation, synthetic, null)

  private def frame(rows: Row*): DataFrame =
    spark.createDataFrame(spark.sparkContext.parallelize(rows, 1), Schemas.ReviewEvents)

  private def config(): JobConfig = {
    val name = UUID.randomUUID().toString
    val output = Files.createDirectories(root.resolve("processed").resolve(name))
    JobConfig(root, root.resolve("unused"), output, job = "stream",
      eventInput = Some(Files.createDirectories(root.resolve("events").resolve(name))),
      checkpoint = Some(root.resolve("checkpoints").resolve(name)), allowSyntheticEvents = true)
  }

  private def snapshot(config: JobConfig, batch: Long, name: String): DataFrame =
    spark.read.parquet(config.output.resolve("committed").resolve("batch-%020d".format(batch)).resolve(name).toString)

  test("probability contracts reject nonfinite, out of range and nonunit distributions") {
    val result = ReviewIngestion.validate(frame(event("a", positive = Double.NaN),
      event("b", positive = 1.2), event("c", positive = 0.8)), allowSynthetic = true)
    assert(result.accepted.count() == 0)
    assert(result.rejected.count() == 3)
  }

  test("synthetic input requires permission and never becomes audience evidence") {
    assert(ReviewIngestion.validate(frame(event("a", synthetic = true)), false).accepted.count() == 0)
    val c = config()
    val result = ReviewStreamJob.processBatch(frame(event("a", synthetic = true)), 0, c)
    assert(result.currentReviews == 1)
    assert(result.liveRealReviews == 0)
    assert(snapshot(c, 0, "movie_analysis_inputs").count() == 0)
  }

  test("replayed checkpoint batch does not count twice or overwrite a committed snapshot") {
    val c = config()
    val input = frame(event("a"), event("a"))
    val first = ReviewStreamJob.processBatch(input, 0, c)
    val replay = ReviewStreamJob.processBatch(input, 0, c)
    assert(first.ledgerEvents == 1)
    assert(!first.replayed && replay.replayed)
    assert(replay.ledgerEvents == 1 && replay.currentReviews == 1)
  }

  test("higher revision replaces analysis; delete tombstone defeats a later stale revision") {
    val c = config()
    ReviewStreamJob.processBatch(frame(event("a")), 0, c)
    ReviewStreamJob.processBatch(frame(event("b", revision = 3, operation = "delete",
      positive = null, neutral = null, negative = null, consent = false, moderation = false, model = null)), 1, c)
    val after = ReviewStreamJob.processBatch(frame(event("c", revision = 2)), 2, c)
    assert(after.currentReviews == 1 && after.liveRealReviews == 0)
    assert(snapshot(c, 2, "current_reviews").head().getAs[String]("operation") == "delete")
    assert(snapshot(c, 2, "active_reviews").count() == 0)
  }

  test("moderation or consent withdrawal removes old eligibility through a higher revision") {
    val c = config()
    ReviewStreamJob.processBatch(frame(event("a")), 0, c)
    val result = ReviewStreamJob.processBatch(frame(event("b", revision = 2, consent = false,
      positive = null, neutral = null, negative = null, model = null)), 1, c)
    assert(result.currentReviews == 1 && result.liveRealReviews == 0)
  }

  test("conflicting event payloads quarantine every affected review rather than retaining old scores") {
    val c = config()
    ReviewStreamJob.processBatch(frame(event("a")), 0, c)
    val result = ReviewStreamJob.processBatch(frame(event("a", positive = 0.1, negative = 0.7)), 1, c)
    assert(result.ledgerEvents == 2 && result.currentReviews == 0)
    assert(snapshot(c, 1, "quarantined_history").count() == 2)
  }

  test("different event IDs cannot silently mutate an immutable review revision or movie identity") {
    val revisionConfig = config()
    ReviewStreamJob.processBatch(frame(event("a")), 0, revisionConfig)
    assert(ReviewStreamJob.processBatch(frame(event("b", positive = 0.1, negative = 0.7)),
      1, revisionConfig).currentReviews == 0)
    val identityConfig = config()
    ReviewStreamJob.processBatch(frame(event("a")), 0, identityConfig)
    assert(ReviewStreamJob.processBatch(frame(event("b", revision = 2, movie = "other-canonical-fixture")),
      1, identityConfig).currentReviews == 0)
  }

  test("model versions remain separate and final audience scores remain null") {
    val c = config()
    ReviewStreamJob.processBatch(frame(event("a"), event("b", review = "review-2", model = "synthetic-model-v2")), 0, c)
    val analytics = snapshot(c, 0, "movie_analysis_inputs")
    assert(analytics.count() == 2)
    assert(analytics.filter(col("audience_sentiment_score").isNotNull).count() == 0)
    assert(analytics.filter(col("score_message") =!= "Not enough audience reviews yet.").count() == 0)
  }

  test("a skipped or reset checkpoint batch is refused") {
    val c = config()
    assertThrows[IllegalArgumentException](ReviewStreamJob.processBatch(frame(event("a")), 1, c))
  }
}
