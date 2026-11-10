package com.movieintel

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import java.util.Comparator

import com.movieintel.analytics.{MovieAnalytics, UserAnalytics}
import com.movieintel.cleaning.{CleanFrames, DataCleaning}
import com.movieintel.config.{JobConfig, Schemas}
import com.movieintel.ingestion.{MovieLensIngestion, RawFrames}
import com.movieintel.transformations.{DataFrameTransformations, RddExamples}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.StructType
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

/** All values here are explicitly synthetic contract fixtures, not real results. */
class BatchPipelineSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var workspace: Path = _
  private var spark: SparkSession = _
  private val stamp = "1009843200"

  override def beforeAll(): Unit = {
    super.beforeAll()
    workspace = Files.createTempDirectory("movieintel-batch-spec-").toRealPath()
    Files.write(workspace.resolve(".owned-by-batch-test"), Array[Byte](1))
    spark = SparkSession.builder().master("local[2]")
      .appName("MovieIntel synthetic batch contract tests")
      .config("spark.ui.enabled", "false")
      .config("spark.driver.host", "127.0.0.1")
      .config("spark.driver.bindAddress", "127.0.0.1")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.shuffle.partitions", "2")
      .config("spark.sql.warehouse.dir", workspace.resolve("warehouse").toUri.toString)
      .config("spark.local.dir", workspace.resolve("scratch").toString)
      .config("spark.movieintel.workspace", workspace.toString)
      .getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
  }

  override def afterAll(): Unit = {
    try {
      if (spark != null) spark.stop()
    } finally {
      // Only the exact test-owned temporary tree may be removed. No following links.
      if (workspace != null && Files.exists(workspace)) {
        val target = workspace.toRealPath()
        require(target.getFileName.toString.startsWith("movieintel-batch-spec-") &&
          Files.isRegularFile(target.resolve(".owned-by-batch-test")),
          "Refusing cleanup of a directory not created by this test suite.")
        val stream = Files.walk(target)
        try stream.sorted(Comparator.reverseOrder[Path]()).forEach { path =>
          require(path.toAbsolutePath.normalize().startsWith(target),
            "Test cleanup escaped its owned temporary workspace.")
          Files.deleteIfExists(path)
          ()
        } finally stream.close()
      }
      super.afterAll()
    }
  }

  private def frame(schema: StructType, rows: Seq[Seq[String]]): DataFrame = {
    val values = rows.map(row => Row.fromSeq(row :+ null))
    spark.createDataFrame(spark.sparkContext.parallelize(values, 2), schema)
  }

  private def fixture(
      extraRatings: Seq[Seq[String]] = Seq.empty,
      extraTags: Seq[Seq[String]] = Seq.empty,
      extraMovies: Seq[Seq[String]] = Seq.empty,
      extraLinks: Seq[Seq[String]] = Seq.empty,
      conflictingTmdb: Boolean = false): RawFrames = {
    val ratings = Seq(
      Seq("1", "1", "4.0", "946684800"),
      Seq("1", "2", "2.0", "978307200"),
      Seq("2", "1", "5.0", stamp)) ++ extraRatings
    val movies = Seq(
      Seq("1", "Synthetic A", "Drama|IMAX"),
      Seq("2", "Synthetic B", "Comedy"),
      Seq("3", "Synthetic Tag Only", "Sci-Fi"),
      Seq("4", "Synthetic No Genre", "(no genres listed)")) ++ extraMovies
    val tags = Seq(Seq("1", "3", " space adventure ", stamp),
      Seq("1", "1", "Visuals score", stamp)) ++ extraTags
    val links = Seq(
      Seq("1", "0000001", if (conflictingTmdb) "999" else "100"),
      Seq("2", "0000002", if (conflictingTmdb) "999" else "200"),
      Seq("3", "0000003", "300"),
      Seq("4", "0000004", "")) ++ extraLinks
    RawFrames(frame(Schemas.RatingsRaw, ratings), frame(Schemas.MoviesRaw, movies),
      frame(Schemas.TagsRaw, tags), frame(Schemas.LinksRaw, links))
  }

  private def clean(): CleanFrames = DataCleaning.clean(fixture())

  test("valid source data preserve namespaces, UTC years and tag-only catalogue items") {
    val result = clean()
    assert(result.ratings.count() == 3)
    assert(result.movies.count() == 4)
    assert(result.tags.count() == 2)
    assert(result.links.count() == 4)
    val row = result.tags.filter(col("movieId") === 3).head()
    assert(row.getAs[String]("tag") == "space adventure")
    assert(row.getAs[String]("tag_raw") == " space adventure ")
    assert(row.getAs[String]("source_user_key") == "movielens-user:1")
    assert(row.getAs[Int]("event_year") == 2002)
    assert(result.movies.filter(col("canonical_movie_id").isNotNull).count() == 0)
    val noGenre = result.movies.filter(col("movieId") === 4).head()
    assert(noGenre.getAs[Seq[String]]("genreArray").isEmpty)
    val format = result.movies.filter(col("movieId") === 1).head()
    assert(format.getAs[Seq[String]]("genreArray") == Seq("Drama"))
    assert(format.getAs[Seq[String]]("source_genres").contains("IMAX"))
    assert(format.getAs[Seq[String]]("format_flags") == Seq("IMAX"))
  }

  test("invalid numbers, non-half ratings, overflow, future times and orphan movies quarantine") {
    val bad = Seq(
      Seq("3", "1", "NaN", stamp), Seq("3", "1", "3.3", stamp),
      Seq("3", "1", "Infinity", stamp), Seq("3", "999", "4.0", stamp),
      Seq("-1", "1", "4.0", stamp), Seq("2147483648", "1", "4.0", stamp),
      Seq("3", "1", "4.0", "9223372036854775807"),
      Seq("3", "1", "4.0", "not-a-timestamp"))
    val result = DataCleaning.clean(fixture(extraRatings = bad))
    assert(result.ratings.count() == 3)
    assert(result.quarantine("ratings").count() == bad.size)
    assert(result.quarantine("ratings").filter(
      col("_quality_reason") === "orphan_rating_movie").count() == 1)
  }

  test("duplicated rating keys are wholly quarantined rather than arbitrarily retained") {
    val result = DataCleaning.clean(fixture(extraRatings = Seq(
      Seq("9", "1", "4.0", stamp), Seq("9", "1", "1.0", stamp))))
    assert(result.ratings.filter(col("userId") === 9).count() == 0)
    assert(result.quarantine("ratings").filter(
      col("_quality_reason") === "duplicate_rating_key").count() == 2)
  }

  test("NBSP-only tags, unknown users/movies and exact duplicate tag events quarantine") {
    val result = DataCleaning.clean(fixture(extraTags = Seq(
      Seq("1", "1", "\u00A0", stamp), Seq("99", "3", "genuine text shape", stamp),
      Seq("1", "99", "unknown movie", stamp), Seq("1", "1", "Visuals score", stamp))))
    assert(result.tags.count() == 1)
    assert(result.quarantine("tags").count() == 5)
    assert(result.quarantine("tags").filter(
      col("_quality_reason") === "duplicate_tag_event").count() == 2)
  }

  test("external conflicts retain source movies and link strings but publish no guessed candidate") {
    val result = DataCleaning.clean(fixture(conflictingTmdb = true))
    assert(result.movies.count() == 4)
    assert(result.links.count() == 4)
    assert(result.quarantine("external_link_conflicts").count() == 2)
    val first = result.links.filter(col("movieId") === 1).head()
    assert(first.getAs[String]("imdbId") == "0000001")
    assert(first.getAs[String]("imdb_id") == "tt0000001")
    assert(first.getAs[String]("tmdbId_raw") == "999")
    assert(first.isNullAt(first.fieldIndex("tmdb_id_candidate")))
    assert(first.getAs[String]("mapping_status") == "conflict")
    assert(!first.getAs[Boolean]("externally_verified"))
    assert(result.links.filter(col("movieId") === 4).head().getAs[String]("mapping_status") == "missing_tmdb")
  }

  test("duplicate movie keys quarantine their source rows and downstream orphan references") {
    val result = DataCleaning.clean(fixture(extraMovies = Seq(Seq("1", "Conflicting title", "Drama"))))
    assert(result.movies.count() == 3)
    assert(result.quarantine("movies").count() == 2)
    assert(result.ratings.count() == 1)
    assert(result.quarantine("ratings").filter(
      col("_quality_reason") === "orphan_rating_movie").count() == 2)
  }

  test("source-key joins conserve rows even when external identifiers conflict") {
    val result = DataCleaning.clean(fixture(conflictingTmdb = true))
    val joined = DataFrameTransformations.transform(result)
    assert(joined.movies.count() == result.movies.count())
    assert(joined.ratings.count() == result.ratings.count())
    assert(joined.tags.count() == result.tags.count())
    assert(DataFrameTransformations.typedRatings(result).filter(_.rating >= 4.0).count() == 2)
  }

  test("movie statistics preserve no-rating nulls and label ratings independently of sentiment") {
    val tables = MovieAnalytics.tables(clean())
    val profile = tables("movie_rating_profiles")
    val rated = profile.filter(col("movieId") === 1).head()
    assert(rated.getAs[Long]("rating_count") == 2)
    assert(math.abs(rated.getAs[Double]("mean_star_rating") - 4.5) < 1e-9)
    val cold = profile.filter(col("movieId") === 3).head()
    assert(cold.getAs[Long]("rating_count") == 0)
    assert(cold.isNullAt(cold.fieldIndex("mean_star_rating")))
    assert(cold.getAs[Boolean]("als_item_cold_start"))
    assert(!profile.columns.exists(_.contains("sentiment")))
  }

  test("user genre calculations are observed rating deviations, not invented match scores") {
    val tables = UserAnalytics.tables(clean())
    val first = tables("source_user_profiles").filter(col("userId") === 1).head()
    assert(first.getAs[Double]("mean_star_rating") == 3.0)
    val drama = tables("source_user_genre_profiles")
      .filter(col("userId") === 1 && col("genre") === "Drama").head()
    assert(drama.getAs[Double]("genre_mean_deviation") == 1.0)
    assert(drama.getAs[Double]("genre_rating_fraction") == 0.5)
    assert(drama.getAs[String]("source_user_key") == "movielens-user:1")
  }

  test("RDD and immutable functional helpers execute genuine tag calculations") {
    assert(RddExamples.normalizeTag("\u00A0").isEmpty)
    assert(RddExamples.positiveIdentifier("42") == Right(42))
    assert(RddExamples.positiveIdentifier("0").isLeft)
    assert(RddExamples.sumTail(List(1L, 2L, 3L)) == 6L)
    val counts = RddExamples.wordCounts(clean().tags).collect().toMap // four-token fixture only
    assert(counts == Map("space" -> 1L, "adventure" -> 1L, "visuals" -> 1L, "score" -> 1L))
  }

  test("bounded header validation rejects wrong schema without changing source files") {
    val input = Files.createDirectories(workspace.resolve("bad-header"))
    Files.write(input.resolve("ratings.csv"), "wrong,header\n".getBytes(StandardCharsets.UTF_8))
    assertThrows[IllegalArgumentException](MovieLensIngestion.read(spark, input))
    assert(new String(Files.readAllBytes(input.resolve("ratings.csv")), StandardCharsets.UTF_8) ==
      "wrong,header\n")
  }

  test("Bronze and Silver Parquet round-trip writes fresh outputs and preserves raw fixtures") {
    val input = Files.createDirectories(workspace.resolve("data/raw/parquet-fixture"))
    val values = Map(
      "ratings.csv" -> "userId,movieId,rating,timestamp\n1,1,4.0,1009843200\n",
      "movies.csv" -> "movieId,title,genres\n1,\"Synthetic \"\"film, quote\"\"\",Drama\n2,Synthetic tag-only,Sci-Fi\n",
      "tags.csv" -> "userId,movieId,tag,timestamp\n1,2,space,1009843200\n",
      "links.csv" -> "movieId,imdbId,tmdbId\n1,0000001,100\n2,0000002,200\n")
    values.foreach { case (name, text) =>
      Files.write(input.resolve(name), text.getBytes(StandardCharsets.UTF_8))
    }
    val output = Files.createDirectories(workspace.resolve("artifacts/parquet-run"))
    val config = JobConfig(workspace = workspace, input = input, output = output,
      inputPartitions = 2, shufflePartitions = 2)
    val bronze = MovieLensIngestion.run(spark, config)
    val silver = DataCleaning.run(spark, bronze, config)
    assert(silver.ratings.count() == 1)
    assert(silver.movies.count() == 2)
    assert(silver.movies.filter(col("movieId") === 1).head().getAs[String]("title") == "Synthetic \"film, quote\"")
    assert(silver.tags.count() == 1)
    values.foreach { case (name, text) =>
      assert(new String(Files.readAllBytes(input.resolve(name)), StandardCharsets.UTF_8) == text)
    }
    assertThrows[Exception](MovieLensIngestion.run(spark, config))
  }

  private def sha256Hex(path: Path): String = {
    val digest = java.security.MessageDigest.getInstance("SHA-256")
    val bytes = Files.readAllBytes(path)
    digest.digest(bytes).map("%02x".format(_)).mkString
  }

  private def countParquetPartFiles(dir: Path): Int = {
    val stream = Files.list(dir)
    try {
      stream.filter(p => Files.isRegularFile(p) && p.getFileName.toString.endsWith(".parquet")).count().toInt
    } finally stream.close()
  }

  test("Bronze Ingestion Integration: four datasets, schema, provenance, metrics, and safety verification") {
    val input = Files.createDirectories(workspace.resolve("data/raw/bronze-integration-fixture"))
    val fixtureData = Map(
      "ratings.csv" -> "userId,movieId,rating,timestamp\n1,10,4.0,1009843200\n1,20,3.5,1009843300\n2,10,5.0,1009843400\n2,30,2.0,1009843500\n",
      "movies.csv" -> "movieId,title,genres\n10,Film Ten (2001),Action|Sci-Fi\n20,Film Twenty (2002),Comedy\n30,Film Thirty (2003),Drama\n",
      "tags.csv" -> "userId,movieId,tag,timestamp\n1,10,cyberpunk,1009843200\n2,30,touching,1009843500\n",
      "links.csv" -> "movieId,imdbId,tmdbId\n10,0000010,1000\n20,0000020,2000\n30,0000030,3000\n")

    val initialHashes = fixtureData.map { case (name, content) =>
      val file = input.resolve(name)
      Files.write(file, content.getBytes(StandardCharsets.UTF_8))
      name -> sha256Hex(file)
    }

    val output = Files.createDirectories(workspace.resolve("artifacts/bronze-integration-run"))
    val configuredPartitions = 2
    val config = JobConfig(workspace = workspace, input = input, output = output,
      inputPartitions = configuredPartitions, shufflePartitions = 2)

    // Execute MovieLensIngestion
    val bronze = MovieLensIngestion.run(spark, config)

    // A. Bronze ingestion verification: 4 directories created, readable, row counts match
    val stages = Seq("ratings" -> 4L, "movies" -> 3L, "tags" -> 2L, "links" -> 3L)
    stages.foreach { case (name, expectedCount) =>
      val stageDir = output.resolve("bronze").resolve(name)
      assert(Files.isDirectory(stageDir), s"Bronze stage directory $name must exist.")
      val reloaded = spark.read.parquet(stageDir.toString)
      assert(reloaded.count() == expectedCount, s"Row count for $name must match fixture.")
    }
    assert(bronze.ratings.count() == 4L)
    assert(bronze.movies.count() == 3L)
    assert(bronze.tags.count() == 2L)
    assert(bronze.links.count() == 3L)

    // B. Partition validation on output
    val frames = Seq(bronze.ratings, bronze.movies, bronze.tags, bronze.links)
    frames.foreach { df =>
      assert(df.rdd.getNumPartitions <= configuredPartitions,
        s"Output RDD partitions (${df.rdd.getNumPartitions}) must not exceed configured $configuredPartitions.")
    }
    stages.foreach { case (name, _) =>
      val partCount = countParquetPartFiles(output.resolve("bronze").resolve(name))
      assert(partCount <= configuredPartitions,
        s"Parquet part file count ($partCount) for $name must not exceed configured $configuredPartitions.")
    }

    // C. Data integrity & provenance verification
    fixtureData.foreach { case (name, originalContent) =>
      val file = input.resolve(name)
      assert(Files.isRegularFile(file), s"Source file $name must still exist.")
      assert(sha256Hex(file) == initialHashes(name), s"Source file $name checksum must be unchanged.")
      val currentContent = new String(Files.readAllBytes(file), StandardCharsets.UTF_8)
      assert(currentContent == originalContent, s"Source content for $name must be unchanged.")
      val firstLine = currentContent.linesIterator.next()
      assert(firstLine == originalContent.linesIterator.next(), s"Original header for $name must be preserved.")
    }

    val provenanceCols = Seq("_source_file", "_source_name", "_ingested_at")
    frames.foreach { df =>
      provenanceCols.foreach { colName =>
        assert(df.columns.contains(colName), s"DataFrame must contain provenance column $colName.")
      }
      val names = df.select("_source_name").distinct().collect().map(_.getString(0))
      assert(names.sameElements(Array("ml-32m")), "_source_name must strictly identify 'ml-32m'.")
    }

    // D. Ingestion Metrics verification
    val reportPath = output.resolve("reports").resolve("ingestion.json")
    assert(Files.isRegularFile(reportPath), "reports/ingestion.json must be written.")
    val reportDf = spark.read.json(reportPath.toString)
    val metrics = reportDf.select("metrics.*")
    assert(metrics.select("ratings_rows").head().getLong(0) == 4L)
    assert(metrics.select("movies_rows").head().getLong(0) == 3L)
    assert(metrics.select("tags_rows").head().getLong(0) == 2L)
    assert(metrics.select("links_rows").head().getLong(0) == 3L)
    assert(metrics.select("requested_partitions").head().getLong(0) == configuredPartitions.toLong)

    // E. Safety verification
    assertThrows[Exception](MovieLensIngestion.run(spark, config))
    assert(output.startsWith(workspace.toRealPath()), "Output must be strictly isolated within temporary workspace.")
    assert(input.startsWith(workspace.toRealPath()), "Input must be strictly isolated within temporary workspace.")
  }

  test("Bronze Ingestion Partition Validation: coalesce enforces partition limits across different configurations") {
    val input = Files.createDirectories(workspace.resolve("data/raw/bronze-partition-fixture"))
    val fixtureData = Map(
      "ratings.csv" -> "userId,movieId,rating,timestamp\n1,1,4.0,1009843200\n2,2,3.5,1009843200\n3,3,5.0,1009843200\n4,4,2.0,1009843200\n",
      "movies.csv" -> "movieId,title,genres\n1,M1,Action\n2,M2,Comedy\n3,M3,Drama\n4,M4,Sci-Fi\n",
      "tags.csv" -> "userId,movieId,tag,timestamp\n1,1,t1,1009843200\n2,2,t2,1009843200\n",
      "links.csv" -> "movieId,imdbId,tmdbId\n1,01,10\n2,02,20\n3,03,30\n4,04,40\n")
    fixtureData.foreach { case (name, content) =>
      Files.write(input.resolve(name), content.getBytes(StandardCharsets.UTF_8))
    }

    // Configuration 1: inputPartitions = 1 (single partition write)
    val outputSingle = Files.createDirectories(workspace.resolve("artifacts/bronze-single-part-run"))
    val configSingle = JobConfig(workspace = workspace, input = input, output = outputSingle,
      inputPartitions = 1, shufflePartitions = 2)
    val bronzeSingle = MovieLensIngestion.run(spark, configSingle)
    Seq(bronzeSingle.ratings, bronzeSingle.movies, bronzeSingle.tags, bronzeSingle.links).foreach { df =>
      assert(df.rdd.getNumPartitions == 1, "coalesce(1) must yield exactly 1 partition.")
    }
    Seq("ratings", "movies", "tags", "links").foreach { name =>
      val parts = countParquetPartFiles(outputSingle.resolve("bronze").resolve(name))
      assert(parts == 1, s"coalesce(1) must write exactly 1 parquet file for $name.")
    }

    // Configuration 2: inputPartitions = 3
    val outputMulti = Files.createDirectories(workspace.resolve("artifacts/bronze-multi-part-run"))
    val configMulti = JobConfig(workspace = workspace, input = input, output = outputMulti,
      inputPartitions = 3, shufflePartitions = 2)
    val bronzeMulti = MovieLensIngestion.run(spark, configMulti)
    Seq(bronzeMulti.ratings, bronzeMulti.movies, bronzeMulti.tags, bronzeMulti.links).foreach { df =>
      assert(df.rdd.getNumPartitions <= 3, "coalesce(3) must not exceed 3 partitions.")
    }
    Seq("ratings", "movies", "tags", "links").foreach { name =>
      val parts = countParquetPartFiles(outputMulti.resolve("bronze").resolve(name))
      assert(parts <= 3, s"coalesce(3) must not exceed 3 parquet files for $name.")
    }
  }
}
