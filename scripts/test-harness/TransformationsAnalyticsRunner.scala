package com.movieintel.harness

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import java.security.MessageDigest
import java.time.Instant
import java.util.Comparator
import scala.collection.mutable.ArrayBuffer

import com.movieintel.analytics.{MovieAnalytics, UserAnalytics}
import com.movieintel.cleaning.{CleanFrames, DataCleaning}
import com.movieintel.config.{JobConfig, PathPolicy, Schemas}
import com.movieintel.ingestion.{MovieLensIngestion, RawFrames}
import com.movieintel.io.JsonCodec
import com.movieintel.transformations.{DataFrameTransformations, FeatureFrames, RddExamples}
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/** Standalone Spark integration test runner for MovieIntel Task 2.4:
  * Silver-to-Gold Transformations, Movie Analytics, User Analytics, and RDD Processing.
  */
object TransformationsAnalyticsRunner {

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
    println("  MOVIEINTEL: STANDALONE TRANSFORMATIONS & ANALYTICS INTEGRATION VALIDATION RUNNER")
    println("=" * 110)

    val workspaceArg = args.sliding(2).collectFirst {
      case Array("--workspace", path) => Paths.get(path)
    }.getOrElse(Paths.get("."))

    val workspace = workspaceArg.toAbsolutePath.normalize().toRealPath()
    println(s"Workspace: $workspace")

    val valRoot = workspace.resolve("artifacts").resolve("analytics-standalone-validation")
    println(s"Validation root: $valRoot")

    val fixtureDir = valRoot.resolve("fixture")
    val runDir = valRoot.resolve("run-analytics")
    val scratchDir = valRoot.resolve("spark-scratch")

    deleteRecursively(fixtureDir)
    deleteRecursively(runDir)
    deleteRecursively(scratchDir)

    Files.createDirectories(fixtureDir)
    Files.createDirectories(scratchDir)

    // Build synthetic fixture datasets designed for analytics validation
    val moviesCsv =
      "movieId,title,genres\n" +
      "10,Film Ten (2001),Action|Sci-Fi|IMAX\n" +
      "20,Film Twenty (2002),Comedy|Romance\n" +
      "30,Film Thirty (2003),(no genres listed)\n" +
      "40,Film Forty (2004),Drama\n" +
      "50,Film Fifty ColdStart (2005),Horror\n"

    val ratingsCsv =
      "userId,movieId,rating,timestamp\n" +
      "1,10,4.0,1009843200\n" +
      "1,20,3.5,1009843300\n" +
      "1,40,4.5,1009843400\n" +
      "2,10,5.0,1009843500\n" +
      "2,20,4.0,1009843600\n" +
      "3,10,4.0,1009843700\n" +
      "3,20,2.0,1009843800\n" +
      "3,30,3.0,1009843900\n" +
      "4,10,4.0,1009844000\n" +
      "4,20,5.0,1009844100\n" +
      "4,40,4.0,1009844200\n" +
      "5,10,5.0,1009844300\n"

    val tagsCsv =
      "userId,movieId,tag,timestamp\n" +
      "1,10,cyberpunk,1009843200\n" +
      "1,10,action adventure,1009843300\n" +
      "2,20,hilarious comedy,1009843400\n" +
      "3,30,minimalist,1009843500\n" +
      "4,50,cold start tag,1009843600\n"

    val linksCsv =
      "movieId,imdbId,tmdbId\n" +
      "10,0000010,1000\n" +
      "20,0000020,2000\n" +
      "30,0000030,\n" +
      "40,0000040,4000\n" +
      "50,0000050,5000\n"

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
      .appName("MovieIntel-Analytics-Validation")
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

      // Execution Pipeline: Bronze Ingestion -> Silver Cleaning -> Transformations -> Analytics
      println("\nStep 1: Running Bronze Ingestion...")
      val rawBronze = MovieLensIngestion.run(spark, config)

      println("Step 2: Running Silver Data Cleaning...")
      val cleanSilver = DataCleaning.run(spark, rawBronze, config)

      println("Step 3: Running Component A (DataFrameTransformations)...")
      val features: FeatureFrames = DataFrameTransformations.run(spark, cleanSilver, config)

      println("Step 4: Running Component B (MovieAnalytics)...")
      val movieMetrics = MovieAnalytics.run(spark, cleanSilver, config)

      println("Step 5: Running Component C (UserAnalytics)...")
      val userMetrics = UserAnalytics.run(spark, cleanSilver, config)

      println("Step 6: Running Component D (RddExamples)...")
      val rddMetrics = RddExamples.run(spark, cleanSilver.tags, config)

      // =========================================================================
      // ASSERTIONS & VERIFICATION
      // =========================================================================
      println("\n" + "-" * 110)
      println("VALIDATING TASK 2.4 COMPONENTS A, B, C, D")
      println("-" * 110)

      // -------------------------------------------------------------------------
      // COMPONENT A: DataFrameTransformations
      // -------------------------------------------------------------------------
      val sourceRatingCount = cleanSilver.ratings.count()
      val joinedRatingCount = features.ratings.count()
      record("A01", "Transformations", "Ratings join cardinality preserved (no row multiplication)",
        s"$sourceRatingCount", s"$joinedRatingCount", sourceRatingCount == joinedRatingCount)

      val sourceMovieCount = cleanSilver.movies.count()
      val joinedMovieCount = features.movies.count()
      record("A02", "Transformations", "Movies join cardinality preserved",
        s"$sourceMovieCount", s"$joinedMovieCount", sourceMovieCount == joinedMovieCount)

      val sourceTagCount = cleanSilver.tags.count()
      val joinedTagCount = features.tags.count()
      record("A03", "Transformations", "Tags join cardinality preserved",
        s"$sourceTagCount", s"$joinedTagCount", sourceTagCount == joinedTagCount)

      // Window ranking function: user_rating_sequence
      val u1Ratings = features.ratings.filter(col("userId") === 1)
        .select("user_rating_sequence", "timestamp").orderBy("user_rating_sequence").collect()
      val seqs = u1Ratings.map(_.getInt(0)).toSeq
      record("A04", "Transformations", "Window function user_rating_sequence is 1, 2, 3...",
        "Seq(1, 2, 3)", seqs.toString(), seqs == Seq(1, 2, 3))

      // Typed Dataset transformation
      val highRatingsDf = spark.read.parquet(config.stage("gold", "typed_high_rating_counts"))
      val u1HighRatings = highRatingsDf.filter(col("userId") === 1).head().getLong(1)
      record("A05", "Transformations", "Typed Dataset high rating count for User 1 (ratings >= 4.0)",
        "2", u1HighRatings.toString, u1HighRatings == 2L)

      // Execution plan reports generated
      val movieJoinPlan = Files.isRegularFile(runDir.resolve("reports/movie_join_plan.txt"))
      val ratingJoinPlan = Files.isRegularFile(runDir.resolve("reports/rating_join_plan.txt"))
      record("A06", "Transformations", "Physical join execution plans written to reports",
        "true", (movieJoinPlan && ratingJoinPlan).toString, movieJoinPlan && ratingJoinPlan)

      // -------------------------------------------------------------------------
      // COMPONENT B: MovieAnalytics
      // -------------------------------------------------------------------------
      val movieProfiles = spark.read.parquet(config.stage("gold", "movie_rating_profiles"))

      // Movie 10: 5 ratings (4.0, 5.0, 4.0, 4.0, 5.0) -> mean = 22.0 / 5 = 4.4
      val m10 = movieProfiles.filter(col("movieId") === 10).head()
      val m10Count = m10.getAs[Long]("rating_count")
      val m10Mean = m10.getAs[Double]("mean_star_rating")
      record("B01", "MovieAnalytics", "Movie 10 total rating count == 5",
        "5", m10Count.toString, m10Count == 5L)
      record("B02", "MovieAnalytics", "Movie 10 mean rating == 4.4",
        "4.40", f"$m10Mean%.2f", math.abs(m10Mean - 4.4) < 1e-4)

      // Cold start movie 50: 0 ratings -> als_item_cold_start == true
      val m50 = movieProfiles.filter(col("movieId") === 50).head()
      val m50ColdStart = m50.getAs[Boolean]("als_item_cold_start")
      val m50TagCount = m50.getAs[Long]("tag_application_count")
      record("B03", "MovieAnalytics", "Movie 50 identified as cold-start (rating_count == 0)",
        "true", m50ColdStart.toString, m50ColdStart)
      record("B04", "MovieAnalytics", "Movie 50 identified as tag-only cold start item",
        "true", (m50ColdStart && m50TagCount > 0L).toString, m50ColdStart && m50TagCount > 0L)

      // Insufficient evidence flag (< 5 ratings)
      val m20 = movieProfiles.filter(col("movieId") === 20).head()
      val m20Count = m20.getAs[Long]("rating_count")
      val m20Insuff = m20.getAs[Boolean]("insufficient_evidence")
      record("B05", "MovieAnalytics", "Movie 20 (4 ratings) flagged insufficient_evidence",
        "true", m20Insuff.toString, m20Count == 4L && m20Insuff)

      // Popularity rank: Movie 10 (count 5) rank 1, Movie 20 (count 4) rank 2
      val m10Rank = m10.getAs[Int]("popularity_rank")
      val m20Rank = m20.getAs[Int]("popularity_rank")
      record("B06", "MovieAnalytics", "Movie popularity rank ordered by rating count",
        "1, 2", s"$m10Rank, $m20Rank", m10Rank == 1 && m20Rank == 2)

      // Genre rating statistics: Action has 5 ratings from Movie 10
      val genreStats = spark.read.parquet(config.stage("gold", "genre_rating_statistics"))
      val actionStats = genreStats.filter(col("genre") === "Action").head()
      val actionCount = actionStats.getAs[Long]("rating_count")
      val actionMean = actionStats.getAs[Double]("mean_star_rating")
      record("B07", "MovieAnalytics", "Action genre rating count == 5",
        "5", actionCount.toString, actionCount == 5L)
      record("B08", "MovieAnalytics", "Action genre mean rating == 4.4",
        "4.40", f"$actionMean%.2f", math.abs(actionMean - 4.4) < 1e-4)

      // Yearly rating trends
      val yearlyActivity = spark.read.parquet(config.stage("gold", "rating_activity_yearly"))
      val totalYearlyRatings = yearlyActivity.select(sum("rating_count")).head().getLong(0)
      record("B09", "MovieAnalytics", "Yearly rating activity aggregate equals total ratings (12)",
        "12", totalYearlyRatings.toString, totalYearlyRatings == 12L)

      // Metadata completeness score
      val m10Completeness = m10.getAs[Double]("metadata_completeness")
      record("B10", "MovieAnalytics", "Metadata completeness score is normalized (0.0 to 1.0)",
        "true", (m10Completeness > 0.0 && m10Completeness <= 1.0).toString, m10Completeness > 0.0 && m10Completeness <= 1.0)

      // -------------------------------------------------------------------------
      // COMPONENT C: UserAnalytics
      // -------------------------------------------------------------------------
      val userProfiles = spark.read.parquet(config.stage("gold", "source_user_profiles"))

      // User 1: 3 ratings (4.0, 3.5, 4.5) -> mean = 12.0 / 3 = 4.0
      val u1 = userProfiles.filter(col("userId") === 1).head()
      val u1Count = u1.getAs[Long]("rating_count")
      val u1Mean = u1.getAs[Double]("mean_star_rating")
      val u1HighCount = u1.getAs[Long]("high_ratings_count")
      val u1LowCount = u1.getAs[Long]("low_ratings_count")
      val u1Span = u1.getAs[Long]("activity_span_seconds")

      record("C01", "UserAnalytics", "User 1 total ratings count == 3",
        "3", u1Count.toString, u1Count == 3L)
      record("C02", "UserAnalytics", "User 1 mean rating == 4.0",
        "4.00", f"$u1Mean%.2f", math.abs(u1Mean - 4.0) < 1e-4)
      record("C03", "UserAnalytics", "User 1 high rating count == 2 (4.0, 4.5)",
        "2", u1HighCount.toString, u1HighCount == 2L)
      record("C04", "UserAnalytics", "User 1 low rating count == 0",
        "0", u1LowCount.toString, u1LowCount == 0L)
      record("C05", "UserAnalytics", "User 1 activity span == 200 seconds (1009843400 - 1009843200)",
        "200", u1Span.toString, u1Span == 200L)

      // Activity tier
      val u1Tier = u1.getAs[String]("activity_tier")
      record("C06", "UserAnalytics", "User 1 (3 ratings) classified as low_activity_user",
        "low_activity_user", u1Tier, u1Tier == "low_activity_user")

      // User genre preferences
      val userGenres = spark.read.parquet(config.stage("gold", "source_user_genre_profiles"))
      val u1Action = userGenres.filter(col("userId") === 1 && col("genre") === "Action").head()
      val u1ActionCount = u1Action.getAs[Long]("genre_rating_count")
      val u1ActionFraction = u1Action.getAs[Double]("genre_rating_fraction")
      record("C07", "UserAnalytics", "User 1 Action rating fraction == 1/3 (0.333)",
        "0.333", f"$u1ActionFraction%.3f", math.abs(u1ActionFraction - (1.0 / 3.0)) < 1e-3)

      // User tag interests: User 1 applied 2 tags to Movie 10
      val userTags = spark.read.parquet(config.stage("gold", "source_user_tag_interests"))
      val u1Cyberpunk = userTags.filter(col("userId") === 1 && col("tag") === "cyberpunk").head()
      val u1TagCount = u1Cyberpunk.getAs[Long]("tag_application_count")
      val u1LogFreq = u1Cyberpunk.getAs[Double]("log_tag_frequency")
      record("C08", "UserAnalytics", "User 1 tag interest count == 1 and log frequency > 0",
        "true", (u1TagCount == 1L && u1LogFreq > 0.0).toString, u1TagCount == 1L && u1LogFreq > 0.0)

      // -------------------------------------------------------------------------
      // COMPONENT D: RddExamples
      // -------------------------------------------------------------------------
      val rddWordCounts = spark.read.parquet(config.stage("gold", "tag_word_counts"))
      val totalTokens = rddWordCounts.select(sum("occurrences")).head().getLong(0)
      record("D01", "RddExamples", "RDD word count tokens produced and saved",
        "> 0", totalTokens.toString, totalTokens > 0L)

      val groupByKeySample = spark.read.parquet(config.stage("gold", "group_by_key_bounded_sample"))
      val sampleRows = groupByKeySample.count()
      record("D02", "RddExamples", "Bounded groupByKey teaching sample executed and saved",
        "> 0", sampleRows.toString, sampleRows > 0L)

      // Equivalence verification: RDD unique token count == DataFrame word count rows
      val rddUniqueTokens = rddMetrics("rdd_unique_tokens")
      val dfWordCountRows = rddMetrics("df_word_count_rows")
      record("D03", "RddExamples", "RDD reduceByKey and DataFrame explode aggregation produce equivalent token counts",
        rddUniqueTokens.toString, dfWordCountRows.toString, rddUniqueTokens == dfWordCountRows)

      // DAG lineage report and architectural performance comparison written
      val rddDagReport = Files.isRegularFile(runDir.resolve("reports/rdd_dag.txt"))
      val rddPerfAnalysis = Files.isRegularFile(runDir.resolve("reports/rdd_performance_analysis.txt"))
      record("D04", "RddExamples", "RDD DAG lineage and reduceByKey vs groupByKey analysis documented",
        "true", (rddDagReport && rddPerfAnalysis).toString, rddDagReport && rddPerfAnalysis)

      // -------------------------------------------------------------------------
      // DATA SAFETY, PARQUET ROUND-TRIP & OVERWRITE PREVENTION
      // -------------------------------------------------------------------------
      val sourceChecksumsMatch = fixtureData.keys.forall { fn =>
        sha256Hex(fixtureDir.resolve(fn)) == initialChecksums(fn)
      }
      record("S01", "DataSafety", "Raw source fixture CSV checksums unmodified after all runs",
        "true", sourceChecksumsMatch.toString, sourceChecksumsMatch)

      var overwriteCaught = false
      var overwriteMsg = ""
      try {
        MovieAnalytics.run(spark, cleanSilver, config)
      } catch {
        case ex: Exception =>
          overwriteCaught = true
          overwriteMsg = ex.getMessage
      }
      record("S02", "DataSafety", "Gold layer overwrite prevention throws when target directory exists",
        "throws Exception", if (overwriteCaught) s"threw (${overwriteMsg.take(40)}...)" else "did not throw", overwriteCaught)

      // -------------------------------------------------------------------------
      // Directory Listing Summary
      // -------------------------------------------------------------------------
      println("\n" + "-" * 110)
      println("GOLD ANALYTICS PARQUET DIRECTORY LISTING")
      println("-" * 110)
      val goldDir = runDir.resolve("gold")
      if (Files.isDirectory(goldDir)) {
        val stageStream = Files.list(goldDir)
        try {
          stageStream.forEach { stage =>
            val fileCount = Files.walk(stage).filter(Files.isRegularFile(_)).count()
            val totalBytes = Files.walk(stage).filter(Files.isRegularFile(_)).mapToLong(Files.size(_)).sum()
            println(f"  Gold Table: ${stage.getFileName}%-30s | Files: $fileCount%2d | Size: $totalBytes%,6d bytes")
          }
        } finally stageStream.close()
      }

      // -------------------------------------------------------------------------
      // Summary Report Table
      // -------------------------------------------------------------------------
      println("\n" + "=" * 110)
      println("                          MOVIEINTEL TASK 2.4 VALIDATION SUMMARY")
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
        "runner" -> "com.movieintel.harness.TransformationsAnalyticsRunner",
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

      val summaryPath = valRoot.resolve("validation_summary.json")
      Files.write(summaryPath, (JsonCodec.encode(summaryReport) + "\n").getBytes(StandardCharsets.UTF_8))
      println(s"\nValidation summary saved to: $summaryPath")

      if (failed > 0) {
        System.err.println(s"\nFATAL: $failed assertions failed.")
        sys.exit(1)
      } else {
        println("\nSUCCESS: All Task 2.4 transformations & analytics assertions passed cleanly.")
      }

    } finally {
      spark.stop()
      println("SparkSession stopped cleanly.")
    }
  }
}

