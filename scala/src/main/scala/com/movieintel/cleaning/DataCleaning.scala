package com.movieintel.cleaning

import java.time.Instant

import com.movieintel.config.JobConfig
import com.movieintel.ingestion.RawFrames
import com.movieintel.io.PipelineIO
import org.apache.spark.sql.{Column, DataFrame, SparkSession}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

final case class CleanFrames(
    ratings: DataFrame,
    movies: DataFrame,
    tags: DataFrame,
    links: DataFrame,
    quarantine: Map[String, DataFrame])

/** Conservative policy: every duplicated source-key row is held for review.
  * No ordering-dependent dropDuplicates(userId,movieId), fuzzy merge or score.
  */
object DataCleaning {
  private def unicodeTrim(value: Column): Column =
    regexp_replace(value, "(?U)^\\s+|\\s+$", "")

  private def originals(frame: DataFrame, fields: Seq[String]): DataFrame =
    fields.foldLeft(frame)((current, field) => current.withColumn(field + "_raw", col(field)))

  private def accepted(frame: DataFrame, valid: Column): DataFrame =
    frame.filter(coalesce(valid, lit(false)))

  private def rejected(frame: DataFrame, valid: Column, reason: String): DataFrame =
    frame.filter(!coalesce(valid, lit(false))).withColumn("_quality_reason", lit(reason))

  private def duplicateKeys(
      frame: DataFrame, keys: Seq[String], reason: String): (DataFrame, DataFrame) = {
    val counted = frame.withColumn("_key_count", count(lit(1)).over(
      Window.partitionBy(keys.map(col): _*)))
    (counted.filter(col("_key_count") === 1).drop("_key_count"),
      counted.filter(col("_key_count") > 1).drop("_key_count")
        .withColumn("_quality_reason", lit(reason)))
  }

  private def combine(frames: DataFrame*): DataFrame =
    frames.reduce((left, right) => left.unionByName(right, allowMissingColumns = true))

  private def timestampValid(maximum: Long): Column =
    col("timestamp").isNotNull && col("timestamp").between(0L, maximum)

  def clean(raw: RawFrames): CleanFrames = {
    val spark = raw.ratings.sparkSession
    require(spark.conf.get("spark.sql.session.timeZone", "UTC") == "UTC",
      "Cleaning requires Spark SQL session timeZone=UTC.")
    val maximumTimestamp = Instant.now().getEpochSecond

    val movieBase = originals(raw.movies, Seq("movieId", "title", "genres"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("title", unicodeTrim(col("title_raw")))
      .withColumn("genres", unicodeTrim(col("genres_raw")))
    val movieValid = col("_corrupt_record").isNull && col("movieId") > 0 &&
      col("title").isNotNull && length(col("title")) > 0 &&
      col("genres").isNotNull && length(col("genres")) > 0
    val (uniqueMovies, duplicateMovies) = duplicateKeys(
      accepted(movieBase, movieValid), Seq("movieId"), "duplicate_movie_key")
    val movies = uniqueMovies
      .withColumn("source_movie_key", concat(lit("movielens:"), col("movieId")))
      .withColumn("canonical_movie_id", lit(null).cast("string"))
      .withColumn("source_genres", when(col("genres") === "(no genres listed)",
        expr("CAST(array() AS ARRAY<STRING>)"))
        .otherwise(array_distinct(split(col("genres"), "\\|"))))
      // Preserve the source labels, while separating the IMAX format from story genres.
      .withColumn("genreArray", array_except(col("source_genres"), array(lit("IMAX"))))
      .withColumn("format_flags", when(array_contains(col("source_genres"), "IMAX"),
        array(lit("IMAX"))).otherwise(expr("CAST(array() AS ARRAY<STRING>)")))
      .withColumn("has_genre_metadata", size(col("genreArray")) > 0)
    val movieIds = movies.select("movieId")

    val ratingBase = originals(raw.ratings, Seq("userId", "movieId", "rating", "timestamp"))
      .withColumn("userId", expr("try_cast(userId AS INT)"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("rating", expr("try_cast(rating AS DOUBLE)"))
      .withColumn("timestamp", expr("try_cast(timestamp AS BIGINT)"))
    val ratingValid = col("_corrupt_record").isNull && col("userId") > 0 &&
      col("movieId") > 0 && col("rating").isNotNull && !isnan(col("rating")) &&
      col("rating").between(0.5, 5.0) &&
      col("rating") * 2.0 === floor(col("rating") * 2.0) &&
      timestampValid(maximumTimestamp)
    val validRatings = accepted(ratingBase, ratingValid)
    val orphanRatings = validRatings.join(movieIds, Seq("movieId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_rating_movie"))
    val (uniqueRatings, duplicateRatings) = duplicateKeys(
      validRatings.join(movieIds, Seq("movieId"), "left_semi"),
      Seq("userId", "movieId"), "duplicate_rating_key")
    val ratings = uniqueRatings
      .withColumn("event_time", expr("timestamp_seconds(timestamp)"))
      .withColumn("event_year", year(col("event_time")))
      .withColumn("source_user_key", concat(lit("movielens-user:"), col("userId")))
      .withColumn("source_movie_key", concat(lit("movielens:"), col("movieId")))
    val userIds = ratings.select("userId").distinct()

    val tagBase = originals(raw.tags, Seq("userId", "movieId", "tag", "timestamp"))
      .withColumn("userId", expr("try_cast(userId AS INT)"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("timestamp", expr("try_cast(timestamp AS BIGINT)"))
      .withColumn("tag", unicodeTrim(col("tag_raw")))
    val tagValid = col("_corrupt_record").isNull && col("userId") > 0 &&
      col("movieId") > 0 && col("tag").isNotNull && length(col("tag")) > 0 &&
      timestampValid(maximumTimestamp)
    val validTags = accepted(tagBase, tagValid)
    val tagMovieOrphans = validTags.join(movieIds, Seq("movieId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_tag_movie"))
    val knownMovieTags = validTags.join(movieIds, Seq("movieId"), "left_semi")
    val tagUserOrphans = knownMovieTags.join(userIds, Seq("userId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_tag_user"))
    val (uniqueTags, duplicateTags) = duplicateKeys(
      knownMovieTags.join(userIds, Seq("userId"), "left_semi"),
      Seq("userId", "movieId", "tag_raw", "timestamp"), "duplicate_tag_event")
    val tags = uniqueTags
      .withColumn("event_time", expr("timestamp_seconds(timestamp)"))
      .withColumn("event_year", year(col("event_time")))
      .withColumn("source_user_key", concat(lit("movielens-user:"), col("userId")))
      .withColumn("source_movie_key", concat(lit("movielens:"), col("movieId")))

    val linkBase = originals(raw.links, Seq("movieId", "imdbId", "tmdbId"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("imdbId", unicodeTrim(col("imdbId_raw")))
      .withColumn("tmdbId", unicodeTrim(col("tmdbId_raw")))
    val tmdbMissing = col("tmdbId").isNull || length(col("tmdbId")) === 0
    val linkValid = col("_corrupt_record").isNull && col("movieId") > 0 &&
      col("imdbId").rlike("^[0-9]+$") &&
      (tmdbMissing || (col("tmdbId").rlike("^[0-9]+$") &&
        expr("try_cast(tmdbId AS BIGINT)") > 0L))
    val validLinks = accepted(linkBase, linkValid)
    val orphanLinks = validLinks.join(movieIds, Seq("movieId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_link_movie"))
    val (uniqueLinks, duplicateLinks) = duplicateKeys(
      validLinks.join(movieIds, Seq("movieId"), "left_semi"),
      Seq("movieId"), "duplicate_link_movie_key")
    val candidates = uniqueLinks
      .withColumn("tmdbId", when(length(col("tmdbId")) > 0, col("tmdbId"))
        .otherwise(lit(null).cast("string")))
      .withColumn("_tmdb_count", count(lit(1)).over(Window.partitionBy("tmdbId")))
      .withColumn("_imdb_count", count(lit(1)).over(Window.partitionBy("imdbId")))
      .withColumn("_external_conflict", (col("tmdbId").isNotNull &&
        col("_tmdb_count") > 1) || col("_imdb_count") > 1)
    val externalConflicts = candidates.filter(col("_external_conflict"))
      .withColumn("_quality_reason", lit("ambiguous_external_movie_relationship"))
    val links = candidates
      .withColumn("tmdb_id_candidate", when(!col("_external_conflict"), col("tmdbId"))
        .otherwise(lit(null).cast("string")))
      .withColumn("imdb_id", when(col("_imdb_count") === 1, concat(lit("tt"), col("imdbId")))
        .otherwise(lit(null).cast("string")))
      .withColumn("mapping_status", when(col("_external_conflict"), lit("conflict"))
        .when(col("tmdbId").isNull, lit("missing_tmdb")).otherwise(lit("provisional")))
      .withColumn("canonical_movie_id", lit(null).cast("string"))
      .withColumn("externally_verified", lit(false))
      .drop("_tmdb_count", "_imdb_count", "_external_conflict")

    CleanFrames(ratings, movies, tags, links, Map(
      "movies" -> combine(rejected(movieBase, movieValid, "invalid_movie_record"), duplicateMovies),
      "ratings" -> combine(rejected(ratingBase, ratingValid, "invalid_rating_record"),
        orphanRatings, duplicateRatings),
      "tags" -> combine(rejected(tagBase, tagValid, "invalid_or_blank_tag_record"),
        tagMovieOrphans, tagUserOrphans, duplicateTags),
      "links" -> combine(rejected(linkBase, linkValid, "invalid_link_record"), orphanLinks, duplicateLinks),
      // Informational relationship quarantine; source link records stay in Silver.
      "external_link_conflicts" -> externalConflicts))
  }

  def run(spark: SparkSession, raw: RawFrames, config: JobConfig): CleanFrames = {
    spark.conf.set("spark.movieintel.workspace", config.workspace.toString)
    val result = clean(raw)
    val acceptedFrames = Map("ratings" -> result.ratings, "movies" -> result.movies,
      "tags" -> result.tags, "links" -> result.links)
    acceptedFrames.foreach { case (name, frame) =>
      val partitions = if (name == "ratings" || name == "tags") Seq("event_year") else Seq.empty
      PipelineIO.writeParquet(frame, config.stage("silver", name), partitions)
    }
    result.quarantine.foreach { case (name, frame) =>
      PipelineIO.writeParquet(frame, config.stage("quarantine", name))
    }
    val materialized = CleanFrames(
      spark.read.parquet(config.stage("silver", "ratings")),
      spark.read.parquet(config.stage("silver", "movies")),
      spark.read.parquet(config.stage("silver", "tags")),
      spark.read.parquet(config.stage("silver", "links")),
      result.quarantine.keys.map(name =>
        name -> spark.read.parquet(config.stage("quarantine", name))).toMap)
    val rawCounts = Map("ratings" -> raw.ratings.count(), "movies" -> raw.movies.count(),
      "tags" -> raw.tags.count(), "links" -> raw.links.count())
    val validCounts = Map("ratings" -> materialized.ratings.count(),
      "movies" -> materialized.movies.count(), "tags" -> materialized.tags.count(),
      "links" -> materialized.links.count())
    val invalidCounts = materialized.quarantine.map { case (name, frame) => name -> frame.count() }
    rawCounts.foreach { case (name, count) =>
      require(count == validCounts(name) + invalidCounts(name),
        "Source row reconciliation failed for " + name)
    }
    val metrics = rawCounts.map { case (name, count) => name + "_input" -> count } ++
      validCounts.map { case (name, count) => name + "_accepted" -> count } ++
      invalidCounts.map { case (name, count) => name + "_quarantined" -> count }
    PipelineIO.recordMetrics(config.output, "cleaning", metrics)
    materialized
  }
}
