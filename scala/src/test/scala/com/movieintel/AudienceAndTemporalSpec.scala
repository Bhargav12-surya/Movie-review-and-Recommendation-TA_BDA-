package com.movieintel

import com.movieintel.analytics.ReviewAnalytics
import com.movieintel.recommendation.TemporalSplit
import java.nio.file.Files
import org.apache.spark.sql.SparkSession
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

/** Explicitly synthetic mechanism fixtures; no model training/performance data. */
class AudienceAndTemporalSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var spark: SparkSession = _
  override def beforeAll(): Unit = {
    super.beforeAll()
    val scratch = Files.createTempDirectory("movieintel-score-time-fixture-")
    spark = SparkSession.builder().master("local[1]").appName("synthetic-score-time-contracts")
      .config("spark.ui.enabled", "false").config("spark.driver.host", "127.0.0.1")
      .config("spark.driver.bindAddress", "127.0.0.1").config("spark.sql.shuffle.partitions", "1")
      .config("spark.sql.warehouse.dir", scratch.resolve("warehouse").toUri.toString).getOrCreate()
  }
  override def afterAll(): Unit = {
    try { if (spark != null) spark.stop() } finally super.afterAll()
  }
  test("audience formula matches the documented Python numeric contract") {
    val session = spark
    import session.implicits._
    val rows = Seq(("m", "r1", "u1", 0.1, 0.2, 0.7, 1.0), ("m", "r2", "u2", 0.1, 0.2, 0.7, 1.0))
      .toDF("movie_id", "review_id", "reviewer_id", "p_negative", "p_neutral", "p_positive", "weight")
    val score = ReviewAnalytics.aggregateEligible(rows, 2, 2, 2.0, 0.0, 50.0).first()
    assert(math.abs(score.getAs[Double]("score") - 80.0) < 1e-9)
    assert(math.abs(score.getAs[Double]("effective_review_count") - 2.0) < 1e-9)
  }
  test("insufficient evidence returns null instead of the population prior") {
    val session = spark
    import session.implicits._
    val rows = Seq(("m", "r1", "u1", 0.1, 0.2, 0.7, 1.0))
      .toDF("movie_id", "review_id", "reviewer_id", "p_negative", "p_neutral", "p_positive", "weight")
    val result = ReviewAnalytics.aggregateEligible(rows, 2, 2, 2.0, 5.0, 50.0).first()
    assert(result.isNullAt(result.fieldIndex("score")))
    assert(result.getAs[String]("message") == "Not enough audience reviews yet.")
  }
  test("global time partitions retain exact source cutoff boundaries") {
    val session = spark
    import session.implicits._
    val rows = Seq((1L, 1L, 4.0, 100L), (1L, 2L, 3.0, 200L), (1L, 3L, 5.0, 300L))
      .toDF("userId", "movieId", "rating", "timestamp")
    val (train, validation, testRows) = TemporalSplit.split(rows, 100L, 200L)
    assert(train.first().getAs[Long]("timestamp") == 100L)
    assert(validation.first().getAs[Long]("timestamp") == 200L)
    assert(testRows.first().getAs[Long]("timestamp") == 300L)
  }
  test("out of range source identities are rejected before Int32 casts") {
    val session = spark
    import session.implicits._
    val rows = Seq((2147483648L, 1L, 4.0, 100L)).toDF("userId", "movieId", "rating", "timestamp")
    intercept[IllegalArgumentException] { TemporalSplit.split(rows, 100L, 200L) }
  }
}
