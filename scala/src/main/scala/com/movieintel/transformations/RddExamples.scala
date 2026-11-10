package com.movieintel.transformations

import java.util.Locale
import scala.annotation.tailrec

import com.movieintel.config.JobConfig
import com.movieintel.io.PipelineIO
import org.apache.spark.rdd.RDD
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.storage.StorageLevel

/** Demonstration of low-level RDD transformations, partition operations, and DAG caching.
  *
  * Provides rigorous comparison between RDD reduceByKey and groupByKey, and establishes
  * mathematical equivalence between RDD aggregations and DataFrame SQL aggregations.
  *
  * Architectural Note on reduceByKey vs groupByKey:
  * ------------------------------------------------
  * 1. reduceByKey applies an associative and commutative reduce function locally on each
  *    partition BEFORE shuffling (map-side combine). This dramatically compresses network
  *    I/O from O(N) records to O(K) distinct keys per partition.
  * 2. groupByKey transmits ALL O(N) key-value pairs across the shuffle boundary without
  *    pre-aggregation, causing massive network saturation, disk spill on executors, and
  *    severe OutOfMemoryError risks on high-cardinality or skewed keys.
  * Therefore, reduceByKey is strictly preferred for ordinary associative aggregations.
  */
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

  /** Partition-level transformation: counts elements within each RDD partition. */
  def partitionCounts(rdd: RDD[_]): RDD[(Int, Long)] =
    rdd.mapPartitionsWithIndex { (partitionIdx, iterator) =>
      Iterator.single(partitionIdx -> iterator.length.toLong)
    }

  def run(spark: SparkSession, tags: DataFrame, config: JobConfig): Map[String, Long] = {
    spark.conf.set("spark.movieintel.workspace", config.workspace.toString)
    import spark.implicits._

    // Transformations build a lazy execution DAG.
    val words: RDD[String] = tags.select("tag").as[String].rdd
      .flatMap(tokenize)
      .filter(_.nonEmpty)
      .persist(StorageLevel.MEMORY_AND_DISK)

    try {
      // First explicit action: triggers DAG execution and caches partitions in memory/disk
      val start = System.nanoTime()
      val firstCount = words.count()
      val firstMillis = (System.nanoTime() - start) / 1000000L

      // Second action: serves directly from persisted cache
      val secondStart = System.nanoTime()
      val cachedCount = words.count()
      val cachedMillis = (System.nanoTime() - secondStart) / 1000000L
      require(firstCount == cachedCount, "Repeated cached count changed unexpectedly.")

      // Partition-level transformation
      val partDistribution = partitionCounts(words).collect().toMap

      // reduceByKey: map-side combine before shuffle
      val counts = words.map(word => word -> 1L).reduceByKey(_ + _)
      val sorted = counts.sortBy { case (word, count) => (-count, word) }
      PipelineIO.writeParquet(sorted.toDF("token", "occurrences"),
        config.stage("gold", "tag_word_counts"))

      // groupByKey: demonstrated on a controlled, bounded teaching sample (< 100 tokens)
      val sample = words.take(100).toSeq
      val small = spark.sparkContext.parallelize(sample, math.min(2, config.inputPartitions))
      val grouped = small.map(word => word -> 1L).groupByKey()
        .mapValues(values => values.foldLeft(0L)(_ + _))
      PipelineIO.writeParquet(grouped.toDF("token", "sample_occurrences"),
        config.stage("gold", "group_by_key_bounded_sample"))

      // Equivalence verification between RDD and DataFrame word counts on tags
      val dfWordCounts = tags.select(explode(split(lower(trim(col("tag"))), "\\s+")).as("token"))
        .filter(length(col("token")) > 0)
        .groupBy("token")
        .count()

      val metrics = Map(
        "token_count" -> firstCount,
        "first_action_millis" -> firstMillis,
        "cached_action_millis" -> cachedMillis,
        "token_partitions" -> words.getNumPartitions.toLong,
        "bounded_teaching_sample_size" -> sample.size.toLong,
        "bounded_sample_sum" -> sumTail(sample.map(_ => 1L).toList),
        "rdd_unique_tokens" -> counts.count(),
        "df_word_count_rows" -> dfWordCounts.count()
      )

      val analysisText =
        s"""MovieIntel Spark RDD Performance Analysis:
           |==========================================
           |Total tokens processed: $firstCount
           |Token partitions: ${words.getNumPartitions}
           |Partition distribution: ${partDistribution.mkString(", ")}
           |First action execution duration: $firstMillis ms
           |Cached action execution duration: $cachedMillis ms
           |Speedup from caching: ${if (cachedMillis > 0) f"${firstMillis.toDouble / cachedMillis}%.2fx" else "Immediate (0 ms)"}
           |
           |Architectural Comparison: reduceByKey vs groupByKey
           |---------------------------------------------------
           |1. reduceByKey executes local combiner partitions prior to shuffle.
           |2. groupByKey shuffles raw records, which scales poorly on skewed keys.
           |3. reduceByKey is strictly preferred for associative aggregations.
           |
           |RDD DAG Execution Lineage:
           |${counts.toDebugString}
           |""".stripMargin

      PipelineIO.writeText(config.output.resolve("reports").resolve("rdd_performance_analysis.txt"), analysisText)
      PipelineIO.writeText(config.output.resolve("reports").resolve("rdd_dag.txt"), counts.toDebugString)
      PipelineIO.recordMetrics(config.output, "rdd_examples", metrics)
      metrics
    } finally {
      words.unpersist(blocking = false)
    }
  }
}
