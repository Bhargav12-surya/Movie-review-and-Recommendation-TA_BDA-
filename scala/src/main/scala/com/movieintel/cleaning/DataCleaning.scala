package com.movieintel.cleaning

import java.nio.file.Path
import java.time.Instant

import com.movieintel.config.JobConfig
import com.movieintel.ingestion.RawFrames
import com.movieintel.io.{JsonCodec, PipelineIO}
import org.apache.spark.sql.{Column, DataFrame, SparkSession}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

final case class CleanFrames(
    ratings: DataFrame,
    movies: DataFrame,
    tags: DataFrame,
    links: DataFrame,
    quarantine: Map[String, DataFrame])

/** Production-grade Silver data cleaning and standardization pipeline.
  *
  * Preserves original source records in Bronze while generating validated Silver Parquet
  * datasets, partitioned by event_year for ratings and tags.
  *
  * Enforces conservative data quality:
  * - Exact duplicates are removed (one copy retained, redundant copies quarantined).
  * - Distinct rating events from the same user/movie at different timestamps are preserved.
  * - Conflicting events at the exact same timestamp are wholly quarantined.
  * - Conflicting catalogue items and ambiguous external links are quarantined.
  * - Complete mathematical row-count reconciliation is maintained.
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

  private def combine(frames: DataFrame*): DataFrame = {
    val active = frames.filter(f => f != null && f.columns.nonEmpty)
    if (active.isEmpty) throw new IllegalArgumentException("Cannot combine empty frame list.")
    active.reduce((left, right) => left.unionByName(right, allowMissingColumns = true))
      .withColumn("_processed_at", current_timestamp())
  }

  private def timestampValid(maximum: Long): Column =
    col("timestamp").isNotNull && col("timestamp").between(0L, maximum)

  def clean(raw: RawFrames): CleanFrames = {
    val spark = raw.ratings.sparkSession
    require(spark.conf.get("spark.sql.session.timeZone", "UTC") == "UTC",
      "Cleaning requires Spark SQL session timeZone=UTC.")
    val maximumTimestamp = Instant.now().getEpochSecond

    // =========================================================================
    // 1. MOVIES CLEANING & STANDARDIZATION
    // =========================================================================
    val movieBase = originals(raw.movies, Seq("movieId", "title", "genres"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("title", unicodeTrim(col("title_raw")))
      .withColumn("genres", unicodeTrim(col("genres_raw")))
    val movieValid = col("_corrupt_record").isNull &&
      col("movieId").isNotNull && col("movieId") > 0 &&
      col("title").isNotNull && length(col("title")) > 0 &&
      col("genres").isNotNull && length(col("genres")) > 0
    val validMovies = accepted(movieBase, movieValid)

    // Deduplicate exact duplicate movie records (same movieId, title_raw, genres_raw)
    val exactMovieWindow = Window.partitionBy("movieId", "title_raw", "genres_raw").orderBy("_source_file")
    val moviesWithExact = validMovies.withColumn("_exact_row", row_number().over(exactMovieWindow))
    val exactDuplicateMovies = moviesWithExact.filter(col("_exact_row") > 1).drop("_exact_row")
      .withColumn("_quality_reason", lit("exact_duplicate_movie_record"))
    val dedupedMovies = moviesWithExact.filter(col("_exact_row") === 1).drop("_exact_row")

    // Conflicting movie metadata: multiple records with the same movieId but differing title/genres
    val movieKeyWindow = Window.partitionBy("movieId")
    val moviesWithKeyCount = dedupedMovies.withColumn("_key_count", count(lit(1)).over(movieKeyWindow))
    val duplicateMovies = moviesWithKeyCount.filter(col("_key_count") > 1).drop("_key_count")
      .withColumn("_quality_reason", lit("duplicate_movie_key"))
    val uniqueMovies = moviesWithKeyCount.filter(col("_key_count") === 1).drop("_key_count")

    val movies = uniqueMovies
      .withColumn("source_movie_key", concat(lit("movielens:"), col("movieId")))
      .withColumn("canonical_movie_id", lit(null).cast("string"))
      .withColumn("source_genres", when(col("genres") === "(no genres listed)",
        expr("CAST(array() AS ARRAY<STRING>)"))
        .otherwise(array_distinct(split(col("genres"), "\\|"))))
      // Separate presentation format flags (e.g. IMAX) from narrative genres
      .withColumn("genreArray", array_except(col("source_genres"), array(lit("IMAX"))))
      .withColumn("format_flags", when(array_contains(col("source_genres"), "IMAX"),
        array(lit("IMAX"))).otherwise(expr("CAST(array() AS ARRAY<STRING>)")))
      .withColumn("has_genre_metadata", size(col("genreArray")) > 0)
    val movieIds = movies.select("movieId")

    // =========================================================================
    // 2. RATINGS CLEANING & STANDARDIZATION
    // =========================================================================
    val ratingBase = originals(raw.ratings, Seq("userId", "movieId", "rating", "timestamp"))
      .withColumn("userId", expr("try_cast(userId AS INT)"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("rating", expr("try_cast(rating AS DOUBLE)"))
      .withColumn("timestamp", expr("try_cast(timestamp AS BIGINT)"))
    val ratingValid = col("_corrupt_record").isNull &&
      col("userId").isNotNull && col("userId") > 0 &&
      col("movieId").isNotNull && col("movieId") > 0 &&
      col("rating").isNotNull && !isnan(col("rating")) &&
      col("rating").between(0.5, 5.0) &&
      col("rating") * 2.0 === floor(col("rating") * 2.0) &&
      timestampValid(maximumTimestamp)
    val validRatings = accepted(ratingBase, ratingValid)

    // Foreign key integrity: movie must exist in accepted movies
    val orphanRatings = validRatings.join(movieIds, Seq("movieId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_rating_movie"))
    val knownRatings = validRatings.join(movieIds, Seq("movieId"), "left_semi")

    // Exact duplicate ratings: exact same (userId, movieId, rating, timestamp)
    val exactRatingWindow = Window.partitionBy("userId", "movieId", "rating", "timestamp").orderBy("_source_file")
    val ratingsWithExact = knownRatings.withColumn("_exact_row", row_number().over(exactRatingWindow))
    val exactDuplicateRatings = ratingsWithExact.filter(col("_exact_row") > 1).drop("_exact_row")
      .withColumn("_quality_reason", lit("exact_duplicate_rating_record"))
    val dedupedRatings = ratingsWithExact.filter(col("_exact_row") === 1).drop("_exact_row")

    // Conflicting rating events at the EXACT SAME timestamp:
    // If a user has conflicting ratings for the same movie at the exact same second, both are quarantined.
    // Distinct rating events from the same user/movie at DIFFERENT timestamps are preserved.
    val ratingTsWindow = Window.partitionBy("userId", "movieId", "timestamp")
    val ratingsWithTsCount = dedupedRatings.withColumn("_ts_count", count(lit(1)).over(ratingTsWindow))
    val duplicateRatings = ratingsWithTsCount.filter(col("_ts_count") > 1).drop("_ts_count")
      .withColumn("_quality_reason", lit("duplicate_rating_key"))
    val uniqueRatings = ratingsWithTsCount.filter(col("_ts_count") === 1).drop("_ts_count")

    val ratings = uniqueRatings
      .withColumn("event_time", expr("timestamp_seconds(timestamp)"))
      .withColumn("event_year", year(col("event_time")))
      .withColumn("source_user_key", concat(lit("movielens-user:"), col("userId")))
      .withColumn("source_movie_key", concat(lit("movielens:"), col("movieId")))
    val userIds = ratings.select("userId").distinct()

    // =========================================================================
    // 3. TAGS CLEANING & STANDARDIZATION
    // =========================================================================
    val tagBase = originals(raw.tags, Seq("userId", "movieId", "tag", "timestamp"))
      .withColumn("userId", expr("try_cast(userId AS INT)"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("timestamp", expr("try_cast(timestamp AS BIGINT)"))
      .withColumn("tag", unicodeTrim(col("tag_raw")))
    val tagValid = col("_corrupt_record").isNull &&
      col("userId").isNotNull && col("userId") > 0 &&
      col("movieId").isNotNull && col("movieId") > 0 &&
      col("tag").isNotNull && length(col("tag")) > 0 &&
      timestampValid(maximumTimestamp)
    val validTags = accepted(tagBase, tagValid)

    val tagMovieOrphans = validTags.join(movieIds, Seq("movieId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_tag_movie"))
    val knownMovieTags = validTags.join(movieIds, Seq("movieId"), "left_semi")

    val tagUserOrphans = knownMovieTags.join(userIds, Seq("userId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_tag_user"))
    val knownTags = knownMovieTags.join(userIds, Seq("userId"), "left_semi")

    // Exact duplicate tags (exact same user, movie, tag, timestamp)
    val exactTagWindow = Window.partitionBy("userId", "movieId", "tag_raw", "timestamp").orderBy("_source_file")
    val tagsWithExact = knownTags.withColumn("_exact_row", row_number().over(exactTagWindow))
    val duplicateTags = tagsWithExact.filter(col("_exact_row") > 1).drop("_exact_row")
      .withColumn("_quality_reason", lit("duplicate_tag_event"))
    val uniqueTags = tagsWithExact.filter(col("_exact_row") === 1).drop("_exact_row")

    val tags = uniqueTags
      .withColumn("event_time", expr("timestamp_seconds(timestamp)"))
      .withColumn("event_year", year(col("event_time")))
      .withColumn("source_user_key", concat(lit("movielens-user:"), col("userId")))
      .withColumn("source_movie_key", concat(lit("movielens:"), col("movieId")))

    // =========================================================================
    // 4. LINKS CLEANING & EXTERNAL CONFLICT RESOLUTION
    // =========================================================================
    val linkBase = originals(raw.links, Seq("movieId", "imdbId", "tmdbId"))
      .withColumn("movieId", expr("try_cast(movieId AS INT)"))
      .withColumn("imdbId", unicodeTrim(col("imdbId_raw")))
      .withColumn("tmdbId", unicodeTrim(col("tmdbId_raw")))
    val tmdbMissing = col("tmdbId").isNull || length(col("tmdbId")) === 0
    val linkValid = col("_corrupt_record").isNull &&
      col("movieId").isNotNull && col("movieId") > 0 &&
      col("imdbId").isNotNull && col("imdbId").rlike("^[0-9]+$") &&
      (tmdbMissing || (col("tmdbId").rlike("^[0-9]+$") &&
        expr("try_cast(tmdbId AS BIGINT)") > 0L))
    val validLinks = accepted(linkBase, linkValid)

    val orphanLinks = validLinks.join(movieIds, Seq("movieId"), "left_anti")
      .withColumn("_quality_reason", lit("orphan_link_movie"))
    val knownLinks = validLinks.join(movieIds, Seq("movieId"), "left_semi")

    // Exact duplicate link records
    val exactLinkWindow = Window.partitionBy("movieId", "imdbId_raw", "tmdbId_raw").orderBy("_source_file")
    val linksWithExact = knownLinks.withColumn("_exact_row", row_number().over(exactLinkWindow))
    val exactDuplicateLinks = linksWithExact.filter(col("_exact_row") > 1).drop("_exact_row")
      .withColumn("_quality_reason", lit("exact_duplicate_link_record"))
    val dedupedLinks = linksWithExact.filter(col("_exact_row") === 1).drop("_exact_row")

    // Conflicting link records: duplicate movieId key with conflicting external IDs
    val linkKeyWindow = Window.partitionBy("movieId")
    val linksWithKeyCount = dedupedLinks.withColumn("_key_count", count(lit(1)).over(linkKeyWindow))
    val duplicateLinks = linksWithKeyCount.filter(col("_key_count") > 1).drop("_key_count")
      .withColumn("_quality_reason", lit("duplicate_link_movie_key"))
    val uniqueLinks = linksWithKeyCount.filter(col("_key_count") === 1).drop("_key_count")

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

    // =========================================================================
    // 5. QUARANTINE MAP ASSEMBLY & COMPLETE RECONCILIATION
    // =========================================================================
    CleanFrames(ratings, movies, tags, links, Map(
      "movies" -> combine(rejected(movieBase, movieValid, "invalid_movie_record"),
        exactDuplicateMovies, duplicateMovies),
      "ratings" -> combine(rejected(ratingBase, ratingValid, "invalid_rating_record"),
        orphanRatings, exactDuplicateRatings, duplicateRatings),
      "tags" -> combine(rejected(tagBase, tagValid, "invalid_or_blank_tag_record"),
        tagMovieOrphans, tagUserOrphans, duplicateTags),
      "links" -> combine(rejected(linkBase, linkValid, "invalid_link_record"),
        orphanLinks, exactDuplicateLinks, duplicateLinks),
      "external_link_conflicts" -> externalConflicts.withColumn("_processed_at", current_timestamp())))
  }

  def generateQualityReport(
      spark: SparkSession,
      raw: RawFrames,
      clean: CleanFrames,
      output: Path
  ): Unit = {
    val rawCounts = Map("ratings" -> raw.ratings.count(), "movies" -> raw.movies.count(),
      "tags" -> raw.tags.count(), "links" -> raw.links.count())
    val acceptedCounts = Map("ratings" -> clean.ratings.count(), "movies" -> clean.movies.count(),
      "tags" -> clean.tags.count(), "links" -> clean.links.count())
    val quarantinedCounts = Map(
      "ratings" -> clean.quarantine("ratings").count(),
      "movies" -> clean.quarantine("movies").count(),
      "tags" -> clean.quarantine("tags").count(),
      "links" -> clean.quarantine("links").count()
    )

    val reconciliation = rawCounts.map { case (name, count) =>
      name -> (count == acceptedCounts(name) + quarantinedCounts(name))
    }

    val quarantineReasons = clean.quarantine.map { case (name, frame) =>
      val counts = frame.groupBy("_quality_reason").count().collect().map(r =>
        r.getString(0) -> r.getLong(1)).toMap
      name -> counts
    }

    val ratingDist = clean.ratings.groupBy("rating").count().collect().map(r =>
      r.getDouble(0).toString -> r.getLong(1)).toMap

    val tsStats = clean.ratings.select(min("timestamp"), max("timestamp")).head()
    val minTs = if (tsStats.isNullAt(0)) 0L else tsStats.getLong(0)
    val maxTs = if (tsStats.isNullAt(1)) 0L else tsStats.getLong(1)

    val moviesWithGenres = clean.movies.filter(col("has_genre_metadata")).count()
    val moviesWithoutGenres = clean.movies.filter(!col("has_genre_metadata")).count()
    val imaxMovies = clean.movies.filter(array_contains(col("format_flags"), "IMAX")).count()

    val missingTmdb = clean.links.filter(col("mapping_status") === "missing_tmdb").count()
    val conflictingLinks = clean.links.filter(col("mapping_status") === "conflict").count()
    val provisionalLinks = clean.links.filter(col("mapping_status") === "provisional").count()

    val percentages = rawCounts.map { case (name, total) =>
      val accPct = if (total > 0) (acceptedCounts(name).toDouble / total.toDouble) * 100.0 else 0.0
      val qPct = if (total > 0) (quarantinedCounts(name).toDouble / total.toDouble) * 100.0 else 0.0
      name -> Map("accepted_percentage" -> accPct, "quarantined_percentage" -> qPct)
    }

    val report: Map[String, Any] = Map(
      "schema_version" -> 1,
      "generated_at" -> Instant.now().toString,
      "reconciliation_passed" -> reconciliation.values.forall(identity),
      "reconciliation" -> reconciliation,
      "counts" -> Map(
        "input" -> rawCounts,
        "accepted" -> acceptedCounts,
        "quarantined" -> quarantinedCounts,
        "percentages" -> percentages
      ),
      "quarantine_reasons" -> quarantineReasons,
      "rating_distribution" -> ratingDist,
      "timestamp_validation" -> Map(
        "min_timestamp" -> minTs,
        "max_timestamp" -> maxTs
      ),
      "genre_statistics" -> Map(
        "movies_with_genres" -> moviesWithGenres,
        "movies_without_genres" -> moviesWithoutGenres,
        "imax_movies" -> imaxMovies
      ),
      "external_links_statistics" -> Map(
        "provisional_count" -> provisionalLinks,
        "missing_tmdb_count" -> missingTmdb,
        "conflicting_external_mapping_count" -> conflictingLinks
      )
    )

    PipelineIO.writeText(output.resolve("reports/silver_quality.json"),
      JsonCodec.encode(report) + "\n")
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
    val invalidCounts = Map(
      "ratings" -> materialized.quarantine("ratings").count(),
      "movies" -> materialized.quarantine("movies").count(),
      "tags" -> materialized.quarantine("tags").count(),
      "links" -> materialized.quarantine("links").count()
    )

    rawCounts.foreach { case (name, count) =>
      require(count == validCounts(name) + invalidCounts(name),
        s"Source row reconciliation failed for $name: input=$count, accepted=${validCounts(name)}, quarantined=${invalidCounts(name)}")
    }

    val metrics = rawCounts.map { case (name, count) => name + "_input" -> count } ++
      validCounts.map { case (name, count) => name + "_accepted" -> count } ++
      invalidCounts.map { case (name, count) => name + "_quarantined" -> count }
    PipelineIO.recordMetrics(config.output, "cleaning", metrics)

    generateQualityReport(spark, raw, materialized, config.output)

    materialized
  }
}
