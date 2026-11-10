package com.movieintel.harness

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import java.security.MessageDigest
import java.time.Instant
import java.util.Comparator
import scala.collection.mutable.ArrayBuffer

import com.movieintel.cleaning.{CleanFrames, DataCleaning}
import com.movieintel.config.{JobConfig, PathPolicy, Schemas}
import com.movieintel.ingestion.{MovieLensIngestion, RawFrames}
import com.movieintel.io.JsonCodec
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/** Standalone Spark integration test runner for MovieIntel Silver Data Cleaning & Standardization.
  *
  * Validates all 19 test requirements from Phase 6 without requiring ScalaTest.
  */
object SilverCleaningRunner {

  case class AssertionResult(
      id: String,
      category: String,
      description: String,
      expected: String,
      actual: String,
      passed: Boolean,
      notes: String = ""
  )

  private val results = ArrayBuffer.empty[AssertionResult]

  private def record(
      id: String,
      category: String,
      description: String,
      expected: String,
      actual: String,
      passed: Boolean,
      notes: String = ""
  ): Boolean = {
    val res = AssertionResult(id, category, description, expected, actual, passed, notes)
    results += res
    val tag = if (passed) "[PASS]" else "[FAIL]"
    println(f"$tag $id%-4s | $category%-24s | $description%-48s | Exp: $expected%-12s | Act: $actual%-12s")
    if (!passed && notes.nonEmpty) println(s"       Details: $notes")
    passed
  }

  private def sha256Hex(path: Path): String = {
    val digest = MessageDigest.getInstance("SHA-256")
    val bytes = Files.readAllBytes(path)
    digest.digest(bytes).map("%02x".format(_)).mkString
  }

  private def deleteRecursively(path: Path): Unit = {
    if (Files.exists(path)) {
      val stream = Files.walk(path)
      try {
        stream.sorted(Comparator.reverseOrder[Path]()).forEach { p =>
          Files.deleteIfExists(p)
          ()
        }
      } finally {
        stream.close()
      }
    }
  }

  def main(args: Array[String]): Unit = {
    println("=" * 110)
    println("  MOVIEINTEL: STANDALONE SILVER DATA ENGINEERING INTEGRATION VALIDATION RUNNER")
    println("=" * 110)

    val workspaceArg = args.sliding(2).collectFirst {
      case Array("--workspace", path) => Paths.get(path)
    }.getOrElse(Paths.get("."))

    val workspace = workspaceArg.toAbsolutePath.normalize().toRealPath()
    println(s"Workspace: $workspace")

    val valRoot = workspace.resolve("artifacts").resolve("silver-standalone-validation")
    println(s"Validation root: $valRoot")

    val fixtureDir = valRoot.resolve("fixture")
    val runDir = valRoot.resolve("run-silver")
    val scratchDir = valRoot.resolve("spark-scratch")

    deleteRecursively(fixtureDir)
    deleteRecursively(runDir)
    deleteRecursively(scratchDir)

    Files.createDirectories(fixtureDir)
    Files.createDirectories(scratchDir)

    // Construct comprehensive synthetic fixture datasets
    val moviesCsv =
      "movieId,title,genres\n" +
      "10,Film Ten (2001),Action|Sci-Fi|IMAX\n" +
      "20,Film Twenty (2002),Comedy\n" +
      "30,Film Thirty (2003),(no genres listed)\n" +
      "40,Film Forty (2004),Drama\n" +
      "50,Film Fifty (2005),Horror\n" +
      "50,Film Fifty Conflicting (2005),Thriller\n" +
      "60,Film Sixty (2006),Animation\n" +
      "60,Film Sixty (2006),Animation\n" +
      "-1,Negative Movie,Comedy\n" +
      "notanid,Bad ID Movie,Drama\n" +
      "70,,Action\n" +
      "80,Film Eighty,\n"

    val ratingsCsv =
      "userId,movieId,rating,timestamp\n" +
      "1,10,4.0,1009843200\n" +
      "1,10,5.0,1009843300\n" +
      "1,20,3.5,1009843400\n" +
      "2,10,0.5,1009843500\n" +
      "2,20,5.0,1009843600\n" +
      "2,30,2.0,1009843700\n" +
      "1,10,4.0,1009843200\n" +
      "3,10,3.3,1009843800\n" +
      "3,10,-1.0,1009843900\n" +
      "3,10,5.5,1009844000\n" +
      "3,10,NaN,1009844100\n" +
      "-1,10,4.0,1009844200\n" +
      "4,-10,4.0,1009844300\n" +
      "4,10,,1009844400\n" +
      "4,10,4.0,\n" +
      "4,10,4.0,-500\n" +
      "4,10,4.0,99999999999\n" +
      "4,999,4.0,1009844500\n" +
      "5,10,4.0,1009844600\n" +
      "5,10,1.0,1009844600\n"

    val tagsCsv =
      "userId,movieId,tag,timestamp\n" +
      "1,10,cyberpunk,1009843200\n" +
      "1,10,  space adventure  ,1009843300\n" +
      "2,20,hilarious,1009843400\n" +
      "1,10,cyberpunk,1009843200\n" +
      "1,10,,1009843500\n" +
      "1,10,   ,1009843600\n" +
      "1,10,\u00A0\u00A0,1009843700\n" +
      "1,999,great,1009843800\n" +
      "999,10,great,1009843900\n" +
      "-1,10,great,1009844000\n" +
      "1,-10,great,1009844100\n"

    val linksCsv =
      "movieId,imdbId,tmdbId\n" +
      "10,0000010,1000\n" +
      "20,0000020,\n" +
      "30,0000030,3000\n" +
      "40,0000040,1000\n" +
      "60,0000060,6000\n" +
      "60,0000060,6000\n" +
      "999,0000999,9000\n" +
      "-1,0000001,100\n" +
      "10,notdigits,1000\n" +
      "10,0000010,-50\n"

    val fixtureData = Map(
      "movies.csv" -> moviesCsv,
      "ratings.csv" -> ratingsCsv,
      "tags.csv" -> tagsCsv,
      "links.csv" -> linksCsv
    )

    val initialChecksums = fixtureData.map { case (fn, content) =>
      val file = fixtureDir.resolve(fn)
      Files.write(file, content.getBytes(StandardCharsets.UTF_8))
      fn -> sha256Hex(file)
    }

    println("Created synthetic fixture datasets:")
    initialChecksums.foreach { case (fn, hash) =>
      println(f"  - $fn%-12s SHA-256: $hash")
    }

    // Initialize local SparkSession
    println("\nInitializing local SparkSession (local[2], driver-memory <= 1G)...")
    val spark = SparkSession.builder()
      .master("local[2]")
      .appName("MovieIntel-Silver-Validation")
      .config("spark.ui.enabled", "false")
      .config("spark.driver.host", "127.0.0.1")
      .config("spark.driver.bindAddress", "127.0.0.1")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.shuffle.partitions", "2")
      .config("spark.sql.warehouse.dir", scratchDir.resolve("warehouse").toUri.toString)
      .config("spark.local.dir", scratchDir.resolve("scratch").toString)
      .config("spark.movieintel.workspace", workspace.toString)
      .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    try {
      val config = JobConfig(
        workspace = workspace,
        input = fixtureDir,
        output = runDir,
        job = "batch",
        master = "local[2]",
        shufflePartitions = 2,
        inputPartitions = 2
      )
      config.validate()

      // Step 1: Execute Bronze Ingestion
      println("\nStep 1: Ingesting Bronze Parquet layers...")
      val rawBronze: RawFrames = MovieLensIngestion.run(spark, config)
      val bronzeRatingsCount = rawBronze.ratings.count()
      val bronzeMoviesCount = rawBronze.movies.count()
      val bronzeTagsCount = rawBronze.tags.count()
      val bronzeLinksCount = rawBronze.links.count()

      println(s"Bronze ingested: ratings=$bronzeRatingsCount, movies=$bronzeMoviesCount, tags=$bronzeTagsCount, links=$bronzeLinksCount")

      // Step 2: Execute Silver Data Cleaning & Standardization
      println("\nStep 2: Executing DataCleaning.run (Silver + Quarantine + Quality Report)...")
      val silverClean: CleanFrames = DataCleaning.run(spark, rawBronze, config)

      // =========================================================================
      // ASSERTIONS COVERING ALL 19 TEST REQUIREMENTS
      // =========================================================================
      println("\n" + "-" * 110)
      println("VALIDATING TEST REQUIREMENTS 1-19")
      println("-" * 110)

      // 1. Valid ratings
      val validRatingRows = silverClean.ratings.select("rating").distinct().collect().map(_.getDouble(0)).toSet
      val expectedSubset = Set(0.5, 2.0, 3.5, 4.0, 5.0)
      record("T01", "Ratings", "Valid half-star ratings accepted (0.5 to 5.0)",
        expectedSubset.mkString(","), validRatingRows.intersect(expectedSubset).mkString(","),
        expectedSubset.subsetOf(validRatingRows))

      // 2. Invalid ratings
      val invalidRatingQuarantine = silverClean.quarantine("ratings")
        .filter(col("_quality_reason") === "invalid_rating_record")
      val badRatingCount = invalidRatingQuarantine.count()
      record("T02", "Ratings", "Invalid ratings quarantined (3.3, -1.0, 5.5, NaN, etc.)",
        ">= 4", badRatingCount.toString, badRatingCount >= 4L)

      // 3. Invalid user/movie IDs
      val invalidUserMovieQuarantine = silverClean.quarantine("ratings")
        .filter(col("userId_raw") === "-1" || col("movieId_raw") === "-10")
      val invalidIdsCount = invalidUserMovieQuarantine.count()
      record("T03", "Ratings", "Invalid/negative userId and movieId quarantined",
        "2", invalidIdsCount.toString, invalidIdsCount == 2L)

      // 4. Null values
      val nullValuesQuarantine = silverClean.quarantine("ratings")
        .filter(col("rating_raw").isNull || length(col("rating_raw")) === 0)
      val nullRatingCount = nullValuesQuarantine.count()
      record("T04", "Ratings", "Null ratings detected and quarantined",
        "1", nullRatingCount.toString, nullRatingCount == 1L)

      // 5. Invalid timestamps
      val invalidTsQuarantine = silverClean.quarantine("ratings")
        .filter(col("timestamp_raw") === "-500" || col("timestamp_raw") === "99999999999" || col("timestamp_raw").isNull || length(col("timestamp_raw")) === 0)
      val invalidTsCount = invalidTsQuarantine.count()
      record("T05", "Ratings", "Invalid timestamps quarantined (negative, future, null)",
        "3", invalidTsCount.toString, invalidTsCount == 3L)

      // 6. Exact duplicate removal
      val exactDupRatings = silverClean.quarantine("ratings")
        .filter(col("_quality_reason") === "exact_duplicate_rating_record")
      val exactDupCount = exactDupRatings.count()
      record("T06", "Ratings", "Exact duplicate rating record quarantined (1 kept, 1 quarantined)",
        "1", exactDupCount.toString, exactDupCount == 1L)

      // 7. Different rating events retained
      val user1Movie10 = silverClean.ratings.filter(col("userId") === 1 && col("movieId") === 10)
      val user1Movie10Count = user1Movie10.count()
      val user1Movie10Timestamps = user1Movie10.select("timestamp").collect().map(_.getLong(0)).toSet
      record("T07", "Ratings", "Different rating events preserved for same user/movie",
        "2", user1Movie10Count.toString, user1Movie10Count == 2L && user1Movie10Timestamps == Set(1009843200L, 1009843300L))

      // 8. Genre array normalization
      val movie10 = silverClean.movies.filter(col("movieId") === 10).head()
      val genreArray10 = movie10.getAs[scala.collection.Seq[String]]("genreArray").toSeq
      val formatFlags10 = movie10.getAs[scala.collection.Seq[String]]("format_flags").toSeq
      val hasGenreMeta10 = movie10.getAs[Boolean]("has_genre_metadata")
      record("T08a", "Movies", "Genre array normalized (IMAX excluded from story genres)",
        "Seq(Action, Sci-Fi)", genreArray10.toString(), genreArray10 == Seq("Action", "Sci-Fi"))
      record("T08b", "Movies", "IMAX separated into format_flags",
        "Seq(IMAX)", formatFlags10.toString(), formatFlags10 == Seq("IMAX"))
      record("T08c", "Movies", "has_genre_metadata is true for narrative genres",
        "true", hasGenreMeta10.toString, hasGenreMeta10)

      // 9. Missing genres
      val movie30 = silverClean.movies.filter(col("movieId") === 30).head()
      val genreArray30 = movie30.getAs[scala.collection.Seq[String]]("genreArray").toSeq
      val hasGenreMeta30 = movie30.getAs[Boolean]("has_genre_metadata")
      val rawGenres30 = movie30.getAs[String]("genres_raw")
      record("T09a", "Movies", "(no genres listed) standardized to empty genreArray",
        "List()", genreArray30.toString(), genreArray30.isEmpty)
      record("T09b", "Movies", "has_genre_metadata is false for (no genres listed)",
        "false", hasGenreMeta30.toString, !hasGenreMeta30)
      record("T09c", "Movies", "Original (no genres listed) preserved in genres_raw",
        "(no genres listed)", rawGenres30, rawGenres30 == "(no genres listed)")

      // 10. Blank and Unicode-whitespace tags
      val blankTagQuarantine = silverClean.quarantine("tags")
        .filter(col("_quality_reason") === "invalid_or_blank_tag_record")
      val blankTagCount = blankTagQuarantine.count()
      record("T10", "Tags", "Blank and Unicode NBSP tags quarantined",
        ">= 3", blankTagCount.toString, blankTagCount >= 3L)

      // 11. IMDb leading-zero preservation
      val link10 = silverClean.links.filter(col("movieId") === 10).head()
      val imdbId10 = link10.getAs[String]("imdbId")
      val imdbFormatted10 = link10.getAs[String]("imdb_id")
      record("T11a", "Links", "IMDb leading zeros preserved as string",
        "0000010", imdbId10, imdbId10 == "0000010")
      record("T11b", "Links", "Silver imdb_id formatted with tt prefix",
        "tt0000010", imdbFormatted10, imdbFormatted10 == "tt0000010")

      // 12. Missing TMDB IDs
      val link20 = silverClean.links.filter(col("movieId") === 20).head()
      val status20 = link20.getAs[String]("mapping_status")
      val tmdbCandidate20 = link20.getAs[String]("tmdb_id_candidate")
      record("T12a", "Links", "Missing TMDB ID flagged as missing_tmdb",
        "missing_tmdb", status20, status20 == "missing_tmdb")
      record("T12b", "Links", "Missing TMDB candidate is null",
        "null", String.valueOf(tmdbCandidate20), tmdbCandidate20 == null)

      // 13. Conflicting external mappings
      val link40 = silverClean.links.filter(col("movieId") === 40).head()
      val status40 = link40.getAs[String]("mapping_status")
      val tmdbCandidate40 = link40.getAs[String]("tmdb_id_candidate")
      record("T13a", "Links", "Duplicate TMDB ID mapped to multiple movies flagged conflict",
        "conflict", status40, status40 == "conflict")
      record("T13b", "Links", "Conflicting TMDB candidate set to null",
        "null", String.valueOf(tmdbCandidate40), tmdbCandidate40 == null)

      // 14. Quarantine correctness
      val requiredQuarantineCols = Seq("_quality_reason", "_processed_at", "_source_file", "_source_name", "_ingested_at")
      Seq("ratings", "movies", "tags", "links").foreach { qName =>
        val qFrame = silverClean.quarantine(qName)
        val hasAllCols = requiredQuarantineCols.forall(qFrame.columns.contains)
        record(s"T14_$qName", "Quarantine", s"Quarantine schema correct for $qName",
          "true", hasAllCols.toString, hasAllCols)
      }

      // 15. Row-count reconciliation
      val rawRatingsCount = rawBronze.ratings.count()
      val silverRatingsCount = silverClean.ratings.count()
      val qRatingsCount = silverClean.quarantine("ratings").count()
      record("T15_ratings", "Reconciliation", "Ratings row count reconciled (input = accepted + quarantined)",
        s"$rawRatingsCount", s"${silverRatingsCount + qRatingsCount}", rawRatingsCount == silverRatingsCount + qRatingsCount)

      val rawMoviesCount = rawBronze.movies.count()
      val silverMoviesCount = silverClean.movies.count()
      val qMoviesCount = silverClean.quarantine("movies").count()
      record("T15_movies", "Reconciliation", "Movies row count reconciled (input = accepted + quarantined)",
        s"$rawMoviesCount", s"${silverMoviesCount + qMoviesCount}", rawMoviesCount == silverMoviesCount + qMoviesCount)

      val rawTagsCount = rawBronze.tags.count()
      val silverTagsCount = silverClean.tags.count()
      val qTagsCount = silverClean.quarantine("tags").count()
      record("T15_tags", "Reconciliation", "Tags row count reconciled (input = accepted + quarantined)",
        s"$rawTagsCount", s"${silverTagsCount + qTagsCount}", rawTagsCount == silverTagsCount + qTagsCount)

      val rawLinksCount = rawBronze.links.count()
      val silverLinksCount = silverClean.links.count()
      val qLinksCount = silverClean.quarantine("links").count()
      record("T15_links", "Reconciliation", "Links row count reconciled (input = accepted + quarantined)",
        s"$rawLinksCount", s"${silverLinksCount + qLinksCount}", rawLinksCount == silverLinksCount + qLinksCount)

      // 16. UTC timestamp correctness
      val sampleRating = silverClean.ratings.filter(col("timestamp") === 1009843200L).head()
      val eventYear = sampleRating.getAs[Int]("event_year")
      val eventTimeStr = sampleRating.getAs[java.sql.Timestamp]("event_time").toString
      record("T16a", "Timestamps", "Timestamp 1009843200 UTC event_year == 2002",
        "2002", eventYear.toString, eventYear == 2002)
      record("T16b", "Timestamps", "Timestamp 1009843200 UTC event_time matches 2002-01-01",
        "2002-01-01...", eventTimeStr.take(10), eventTimeStr.startsWith("2002-01-01"))

      // 17. Parquet round-trip
      val reloadedSilverRatings = spark.read.parquet(config.stage("silver", "ratings")).count()
      val reloadedSilverMovies = spark.read.parquet(config.stage("silver", "movies")).count()
      val reloadedSilverTags = spark.read.parquet(config.stage("silver", "tags")).count()
      val reloadedSilverLinks = spark.read.parquet(config.stage("silver", "links")).count()

      record("T17_ratings", "Parquet Round-Trip", "Silver ratings reloaded from disk matches in-memory",
        silverRatingsCount.toString, reloadedSilverRatings.toString, reloadedSilverRatings == silverRatingsCount)
      record("T17_movies", "Parquet Round-Trip", "Silver movies reloaded from disk matches in-memory",
        silverMoviesCount.toString, reloadedSilverMovies.toString, reloadedSilverMovies == silverMoviesCount)
      record("T17_tags", "Parquet Round-Trip", "Silver tags reloaded from disk matches in-memory",
        silverTagsCount.toString, reloadedSilverTags.toString, reloadedSilverTags == silverTagsCount)
      record("T17_links", "Parquet Round-Trip", "Silver links reloaded from disk matches in-memory",
        silverLinksCount.toString, reloadedSilverLinks.toString, reloadedSilverLinks == silverLinksCount)

      // 18. Raw input checksum preservation
      val sourceChecksumsMatch = fixtureData.keys.forall { fn =>
        sha256Hex(fixtureDir.resolve(fn)) == initialChecksums(fn)
      }
      record("T18", "Data Safety", "Raw source CSV checksums unchanged after all runs",
        "true", sourceChecksumsMatch.toString, sourceChecksumsMatch)

      // 19. Existing-output overwrite prevention
      var overwriteCaught = false
      var overwriteExMsg = ""
      try {
        DataCleaning.run(spark, rawBronze, config)
      } catch {
        case ex: Exception =>
          overwriteCaught = true
          overwriteExMsg = ex.getMessage
      }
      record("T19", "Data Safety", "Overwrite prevention throws when target directory exists",
        "throws Exception", if (overwriteCaught) s"threw (${overwriteExMsg.take(40)}...)" else "did not throw", overwriteCaught)

      // Verify Quality Report file
      val qualityReportFile = runDir.resolve("reports/silver_quality.json")
      val qualityReportExists = Files.isRegularFile(qualityReportFile)
      record("T20", "Reports", "reports/silver_quality.json generated on disk",
        "true", qualityReportExists.toString, qualityReportExists)

      if (qualityReportExists) {
        val jsonText = new String(Files.readAllBytes(qualityReportFile), StandardCharsets.UTF_8)
        println(s"\nQuality Report JSON:\n$jsonText")
      }

      // -------------------------------------------------------------------------
      // Directory Listing Summary
      // -------------------------------------------------------------------------
      println("\n" + "-" * 110)
      println("SILVER & QUARANTINE PARQUET DIRECTORY LISTING")
      println("-" * 110)
      Seq("silver", "quarantine").foreach { layer =>
        val layerDir = runDir.resolve(layer)
        if (Files.isDirectory(layerDir)) {
          val stageStream = Files.list(layerDir)
          try {
            stageStream.forEach { stage =>
              val fileCount = Files.walk(stage).filter(Files.isRegularFile(_)).count()
              val totalBytes = Files.walk(stage).filter(Files.isRegularFile(_)).mapToLong(Files.size(_)).sum()
              println(f"  Layer: $layer%-11s | Stage: ${stage.getFileName}%-12s | Files: $fileCount%2d | Size: $totalBytes%,6d bytes")
            }
          } finally stageStream.close()
        }
      }

      // -------------------------------------------------------------------------
      // Summary Report Table
      // -------------------------------------------------------------------------
      println("\n" + "=" * 110)
      println("                          MOVIEINTEL SILVER VALIDATION SUMMARY")
      println("=" * 110)
      println(f"${"ID"}%-5s | ${"Category"}%-24s | ${"Assertion / Contract"}%-48s | ${"Expected"}%-12s | ${"Actual"}%-12s | ${"Status"}%-6s")
      println("-" * 118)

      results.foreach { r =>
        val status = if (r.passed) "PASS" else "FAIL"
        println(f"${r.id}%-5s | ${r.category}%-24s | ${r.description}%-48s | ${r.expected}%-12s | ${r.actual}%-12s | $status%-6s")
      }
      println("-" * 118)

      val total = results.size
      val passed = results.count(_.passed)
      val failed = results.count(!_.passed)
      println(s"TOTAL ASSERTIONS: $total | PASSED: $passed | FAILED: $failed")

      val summaryReport = Map(
        "schema_version" -> 1,
        "runner" -> "com.movieintel.harness.SilverCleaningRunner",
        "generated_at" -> Instant.now().toString,
        "spark_version" -> spark.version,
        "total_assertions" -> total,
        "passed_assertions" -> passed,
        "failed_assertions" -> failed,
        "all_passed" -> (failed == 0),
        "results" -> results.map { r =>
          Map(
            "id" -> r.id,
            "category" -> r.category,
            "description" -> r.description,
            "expected" -> r.expected,
            "actual" -> r.actual,
            "passed" -> r.passed
          )
        }.toSeq
      )

      val summaryPath = valRoot.resolve("silver_validation_summary.json")
      Files.write(summaryPath, (JsonCodec.encode(summaryReport) + "\n").getBytes(StandardCharsets.UTF_8))
      println(s"\nValidation summary saved to: $summaryPath")

      if (failed > 0) {
        System.err.println(s"\nFATAL: $failed assertions failed.")
        sys.exit(1)
      } else {
        println("\nSUCCESS: All Silver cleaning & quarantine assertions passed cleanly.")
      }

    } finally {
      spark.stop()
      println("SparkSession stopped cleanly.")
    }
  }
}

