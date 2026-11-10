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

  test("Bronze ingestion with coalesce preserves all four sources, bounds partitions, and protects raw inputs and overwrite") {
    val input = Files.createDirectories(workspace.resolve("data/raw/bronze-coalesce-fixture"))
    val values = Map(
      "ratings.csv" -> "userId,movieId,rating,timestamp\n1,1,4.0,1009843200\n2,2,3.5,1009843200\n",
      "movies.csv" -> "movieId,title,genres\n1,Synthetic A,Drama\n2,Synthetic B,Comedy\n",
      "tags.csv" -> "userId,movieId,tag,timestamp\n1,1,classic,1009843200\n",
      "links.csv" -> "movieId,imdbId,tmdbId\n1,0000001,100\n2,0000002,200\n")
    values.foreach { case (name, text) =>
      Files.write(input.resolve(name), text.getBytes(StandardCharsets.UTF_8))
    }
    val output = Files.createDirectories(workspace.resolve("artifacts/bronze-coalesce-run"))
    val maxPartitions = 2
    val config = JobConfig(workspace = workspace, input = input, output = output,
      inputPartitions = maxPartitions, shufflePartitions = 2)

    val bronze = MovieLensIngestion.run(spark, config)

    assert(bronze.ratings.count() == 2)
    assert(bronze.movies.count() == 2)
    assert(bronze.tags.count() == 1)
    assert(bronze.links.count() == 2)

    assert(bronze.ratings.rdd.getNumPartitions <= maxPartitions)
    assert(bronze.movies.rdd.getNumPartitions <= maxPartitions)
    assert(bronze.tags.rdd.getNumPartitions <= maxPartitions)
    assert(bronze.links.rdd.getNumPartitions <= maxPartitions)

    values.foreach { case (name, text) =>
      assert(new String(Files.readAllBytes(input.resolve(name)), StandardCharsets.UTF_8) == text)
    }

    assertThrows[Exception](MovieLensIngestion.run(spark, config))
  }
}
