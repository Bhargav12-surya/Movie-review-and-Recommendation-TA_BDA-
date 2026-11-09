package com.movieintel.transformations

import java.util.Locale
import scala.annotation.tailrec

import com.movieintel.config.JobConfig
import com.movieintel.io.PipelineIO
import org.apache.spark.rdd.RDD
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.storage.StorageLevel

object RddExamples {
  final case class SourceTag(movieId: Int, tag: String)
  final case class RatingExample(userId: Int, movieId: Int, rating: Double)

  def normalizeTag(value: String): Option[String] =
    Option(value).map(_.replaceAll("(?U)^\\s+|\\s+$", "").toLowerCase(Locale.ROOT)).filter(_.nonEmpty)

  def positiveIdentifier(value: String): Either[String, Int] =
    Option(value).flatMap(_.toIntOption).filter(_ > 0)
      .toRight("Expected a positive source integer ID.")

  def tokenize(value: String): Vector[String] =
    normalizeTag(value).toVector.flatMap(_.replaceAll("[^\\p{L}\\p{N}]+", " ")
      .trim.split("\\s+").filter(_.nonEmpty)).toVector

  @tailrec def sumTail(values: List[Long], total: Long = 0L): Long = values match {
    case Nil => total
    case head :: tail => sumTail(tail, total + head)
  }

  def wordCounts(tags: DataFrame): RDD[(String, Long)] = {
    val words = tags.select("tag").rdd
      .flatMap(row => Option(row.getString(0)).toSeq)
      .flatMap(tokenize)
      .filter(_.nonEmpty)
    words.map(word => word -> 1L).reduceByKey(_ + _)
  }

  def run(spark: SparkSession, tags: DataFrame, config: JobConfig): Map[String, Long] = {
    spark.conf.set("spark.movieintel.workspace", config.workspace.toString)
    import spark.implicits._
    val words = tags.select("tag").as[String].rdd.flatMap(tokenize)
      .filter(_.nonEmpty).persist(StorageLevel.MEMORY_AND_DISK)
    try {
      // Transformations above build a DAG. count is the first explicit data action.
      val start = System.nanoTime()
      val firstCount = words.count()
      val firstMillis = (System.nanoTime() - start) / 1000000L
      val secondStart = System.nanoTime()
      val cachedCount = words.count()
      val cachedMillis = (System.nanoTime() - secondStart) / 1000000L
      require(firstCount == cachedCount, "Repeated cached count changed unexpectedly.")
      val counts = words.map(word => word -> 1L).reduceByKey(_ + _)
      val sorted = counts.sortBy { case (word, count) => (-count, word) }
      PipelineIO.writeParquet(sorted.toDF("token", "occurrences"),
        config.stage("gold", "tag_word_counts"))
      // groupByKey is deliberately restricted to at most 100 teaching tokens.
      val sample = words.take(100).toSeq
      val small = spark.sparkContext.parallelize(sample, math.min(2, config.inputPartitions))
      val grouped = small.map(word => word -> 1L).groupByKey()
        .mapValues(values => values.foldLeft(0L)(_ + _))
      PipelineIO.writeParquet(grouped.toDF("token", "sample_occurrences"),
        config.stage("gold", "group_by_key_bounded_sample"))
      val metrics = Map("token_count" -> firstCount,
        "first_action_millis" -> firstMillis, "cached_action_millis" -> cachedMillis,
        "token_partitions" -> words.getNumPartitions.toLong,
        "bounded_teaching_sample_size" -> sample.size.toLong,
        "bounded_sample_sum" -> sumTail(sample.map(_ => 1L).toList))
      PipelineIO.writeText(config.output.resolve("reports").resolve("rdd_dag.txt"),
        counts.toDebugString)
      PipelineIO.recordMetrics(config.output, "rdd_examples", metrics)
      metrics
    } finally words.unpersist(blocking = false)
  }
}
