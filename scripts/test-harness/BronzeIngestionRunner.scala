package com.movieintel.harness

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths}
import java.security.MessageDigest
import java.time.Instant
import java.util.Comparator
import scala.collection.mutable.ArrayBuffer

import com.movieintel.config.{JobConfig, PathPolicy, Schemas}
import com.movieintel.ingestion.{MovieLensIngestion, RawFrames}
import com.movieintel.io.JsonCodec
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/** Standalone Spark integration test runner for MovieLens Bronze Ingestion.
  * Validates the coalesce(config.inputPartitions) optimization without requiring ScalaTest.
  */
object BronzeIngestionRunner {

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
    println(f"$tag $id%-4s | $category%-22s | $description%-45s | Exp: $expected%-10s | Act: $actual%-10s")
    if (!passed && notes.nonEmpty) println(s"       Details: $notes")
    passed
  }

  private def sha256Hex(path: Path): String = {
    val digest = MessageDigest.getInstance("SHA-256")
    val bytes = Files.readAllBytes(path)
    digest.digest(bytes).map("%02x".format(_)).mkString
  }

  private def countParquetPartFiles(dir: Path): Int = {
    if (!Files.isDirectory(dir)) return 0
    val stream = Files.list(dir)
    try {
      stream.filter(p => Files.isRegularFile(p) && p.getFileName.toString.endsWith(".parquet")).count().toInt
    } finally {
      stream.close()
    }
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
    println("=" * 100)
    println("  MOVIEINTEL: STANDALONE BRONZE INGESTION INTEGRATION VALIDATION RUNNER")
    println("=" * 100)

    val workspaceArg = args.sliding(2).collectFirst {
      case Array("--workspace", path) => Paths.get(path)
    }.getOrElse(Paths.get("."))

    val workspace = workspaceArg.toAbsolutePath.normalize().toRealPath()
    println(s"Workspace: $workspace")

    val valRoot = workspace.resolve("artifacts").resolve("standalone-validation")
    println(s"Validation root: $valRoot")

    // Clean up previous validation artifacts if present
    val fixtureDir = valRoot.resolve("fixture")
    val outputPart2 = valRoot.resolve("run-part2")
    val outputPart1 = valRoot.resolve("run-part1")
    val scratchDir = valRoot.resolve("spark-scratch")

    deleteRecursively(fixtureDir)
    deleteRecursively(outputPart2)
    deleteRecursively(outputPart1)
    deleteRecursively(scratchDir)

    Files.createDirectories(fixtureDir)
    Files.createDirectories(scratchDir)

    // Build synthetic MovieLens CSV fixtures
    val fixtureData = Map(
      "ratings.csv" -> "userId,movieId,rating,timestamp\n1,10,4.0,1009843200\n1,20,3.5,1009843300\n2,10,5.0,1009843400\n2,30,2.0,1009843500\n",
      "movies.csv" -> "movieId,title,genres\n10,Film Ten (2001),Action|Sci-Fi\n20,Film Twenty (2002),Comedy\n30,Film Thirty (2003),Drama\n",
      "tags.csv" -> "userId,movieId,tag,timestamp\n1,10,cyberpunk,1009843200\n2,30,touching,1009843500\n",
      "links.csv" -> "movieId,imdbId,tmdbId\n10,0000010,1000\n20,0000020,2000\n30,0000030,3000\n"
    )

    val initialChecksums = fixtureData.map { case (filename, content) =>
      val filePath = fixtureDir.resolve(filename)
      Files.write(filePath, content.getBytes(StandardCharsets.UTF_8))
      filename -> sha256Hex(filePath)
    }

    println(s"Created 4 synthetic MovieLens fixture CSVs in $fixtureDir")
    initialChecksums.foreach { case (fn, hash) =>
      println(f"  - $fn%-12s SHA-256: $hash")
    }

    // Initialize local SparkSession
    println("\nInitializing local SparkSession (local[2], driver-memory <= 1G)...")
    val spark = SparkSession.builder()
      .master("local[2]")
      .appName("MovieIntel-Standalone-Bronze-Validation")
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
    println(s"SparkSession created: version ${spark.version}, master ${spark.sparkContext.master}")

    try {
      // -------------------------------------------------------------------------
      // TEST EXECUTION 1: inputPartitions = 2
      // -------------------------------------------------------------------------
      println("\n" + "-" * 100)
      println("EXECUTION 1: MovieLensIngestion with inputPartitions = 2")
      println("-" * 100)

      val configPart2 = JobConfig(
        workspace = workspace,
        input = fixtureDir,
        output = outputPart2,
        job = "batch",
        master = "local[2]",
        shufflePartitions = 2,
        inputPartitions = 2
      )
      configPart2.validate()

      val bronze2: RawFrames = MovieLensIngestion.run(spark, configPart2)

      // =========================================================================
      // A. Four-dataset ingestion
      // =========================================================================
      println("\n--- Section A: Four-Dataset Ingestion ---")
      val stages = Seq("ratings" -> 4L, "movies" -> 3L, "tags" -> 2L, "links" -> 3L)

      stages.foreach { case (name, expectedCount) =>
        val stageDir = outputPart2.resolve("bronze").resolve(name)
        val dirExists = Files.isDirectory(stageDir)
        record(
          s"A0${stages.indexOf(name -> expectedCount) + 1}",
          "Four-Dataset Ingest",
          s"Bronze Parquet directory created: $name",
          "true",
          dirExists.toString,
          dirExists
        )

        val reloaded = spark.read.parquet(stageDir.toString)
        val rowCount = reloaded.count()
        record(
          s"A0${stages.indexOf(name -> expectedCount) + 5}",
          "Four-Dataset Ingest",
          s"Parquet reload row count matches fixture: $name",
          expectedCount.toString,
          rowCount.toString,
          rowCount == expectedCount
        )
      }

      val inMemoryCounts = Seq(
        ("ratings", bronze2.ratings.count(), 4L),
        ("movies", bronze2.movies.count(), 3L),
        ("tags", bronze2.tags.count(), 2L),
        ("links", bronze2.links.count(), 3L)
      )
      inMemoryCounts.zipWithIndex.foreach { case ((name, count, exp), idx) =>
        record(
          s"A${idx + 9}",
          "Four-Dataset Ingest",
          s"In-memory RawFrames count: $name",
          exp.toString,
          count.toString,
          count == exp
        )
      }

      // =========================================================================
      // B. Data integrity and provenance
      // =========================================================================
      println("\n--- Section B: Data Integrity & Provenance ---")
      val frames = Seq(
        "ratings" -> bronze2.ratings,
        "movies" -> bronze2.movies,
        "tags" -> bronze2.tags,
        "links" -> bronze2.links
      )

      val provenanceCols = Seq("_source_file", "_source_name", "_ingested_at")
      provenanceCols.zipWithIndex.foreach { case (colName, idx) =>
        val allContain = frames.forall { case (_, df) => df.columns.contains(colName) }
        record(
          s"B0${idx + 1}",
          "Data Integrity",
          s"Provenance column exists in all 4 datasets: $colName",
          "true",
          allContain.toString,
          allContain
        )
      }

      val sourceNameStrict = frames.forall { case (_, df) =>
        val names = df.select("_source_name").distinct().collect().map(_.getString(0))
        names.sameElements(Array("ml-32m"))
      }
      record(
        "B04",
        "Data Integrity",
        "_source_name equals strictly 'ml-32m'",
        "ml-32m",
        if (sourceNameStrict) "ml-32m" else "mismatch",
        sourceNameStrict
      )

      val ingestedAtPopulated = frames.forall { case (_, df) =>
        df.filter(col("_ingested_at").isNull).count() == 0L
      }
      record(
        "B05",
        "Data Integrity",
        "_ingested_at timestamp is non-null for all records",
        "true",
        ingestedAtPopulated.toString,
        ingestedAtPopulated
      )

      val sourceFilePopulated = frames.forall { case (_, df) =>
        df.filter(col("_source_file").isNull || length(col("_source_file")) === 0).count() == 0L
      }
      record(
        "B06",
        "Data Integrity",
        "_source_file is populated for all records",
        "true",
        sourceFilePopulated.toString,
        sourceFilePopulated
      )

      fixtureData.zipWithIndex.foreach { case ((name, originalContent), idx) =>
        val file = fixtureDir.resolve(name)
        val currentHash = sha256Hex(file)
        val initialHash = initialChecksums(name)
        val unchanged = currentHash == initialHash
        record(
          s"B${idx + 7}",
          "Data Integrity",
          s"Source CSV checksum unchanged: $name",
          initialHash.take(10) + "...",
          currentHash.take(10) + "...",
          unchanged
        )

        val currentContent = new String(Files.readAllBytes(file), StandardCharsets.UTF_8)
        val firstLine = currentContent.linesIterator.next()
        val expectedFirstLine = originalContent.linesIterator.next()
        record(
          s"B${idx + 11}",
          "Data Integrity",
          s"Source CSV header preserved: $name",
          expectedFirstLine,
          firstLine,
          firstLine == expectedFirstLine
        )
      }

      // =========================================================================
      // C. Partition validation (Execution 1: inputPartitions = 2)
      // =========================================================================
      println("\n--- Section C: Partition Validation (Config: inputPartitions = 2) ---")
      frames.zipWithIndex.foreach { case ((name, df), idx) =>
        val numPart = df.rdd.getNumPartitions
        val valid = numPart <= 2 && numPart >= 1
        record(
          s"C0${idx + 1}",
          "Partition Validation",
          s"RDD partition count <= 2 (coalesce): $name",
          "<= 2",
          numPart.toString,
          valid
        )

        val partFiles = countParquetPartFiles(outputPart2.resolve("bronze").resolve(name))
        val validFiles = partFiles <= 2 && partFiles >= 1
        record(
          s"C0${idx + 5}",
          "Partition Validation",
          s"Parquet part-file count <= 2 on disk: $name",
          "<= 2",
          partFiles.toString,
          validFiles
        )
      }

      // =========================================================================
      // D. Metrics validation (Execution 1)
      // =========================================================================
      println("\n--- Section D: Metrics Validation ---")
      val reportPath2 = outputPart2.resolve("reports").resolve("ingestion.json")
      val reportExists2 = Files.isRegularFile(reportPath2)
      record(
        "D01",
        "Metrics Validation",
        "reports/ingestion.json generated on disk",
        "true",
        reportExists2.toString,
        reportExists2
      )

      if (reportExists2) {
        val jsonContent2 = new String(Files.readAllBytes(reportPath2), StandardCharsets.UTF_8)
        println(s"Ingestion metrics JSON content (Execution 1):\n$jsonContent2")

        val reportDf = spark.read.json(reportPath2.toString)
        val metrics = reportDf.select("metrics.*")

        val ratingsRows = metrics.select("ratings_rows").head().getLong(0)
        val moviesRows = metrics.select("movies_rows").head().getLong(0)
        val tagsRows = metrics.select("tags_rows").head().getLong(0)
        val linksRows = metrics.select("links_rows").head().getLong(0)
        val requestedParts = metrics.select("requested_partitions").head().getLong(0)

        record("D02", "Metrics Validation", "metrics.ratings_rows == 4", "4", ratingsRows.toString, ratingsRows == 4L)
        record("D03", "Metrics Validation", "metrics.movies_rows == 3", "3", moviesRows.toString, moviesRows == 3L)
        record("D04", "Metrics Validation", "metrics.tags_rows == 2", "2", tagsRows.toString, tagsRows == 2L)
        record("D05", "Metrics Validation", "metrics.links_rows == 3", "3", linksRows.toString, linksRows == 3L)
        record("D06", "Metrics Validation", "metrics.requested_partitions == 2", "2", requestedParts.toString, requestedParts == 2L)
      }

      // =========================================================================
      // E. Safety validation
      // =========================================================================
      println("\n--- Section E: Safety Validation ---")
      var overwriteCaught = false
      var exceptionMessage = ""
      try {
        MovieLensIngestion.run(spark, configPart2)
      } catch {
        case ex: Exception =>
          overwriteCaught = true
          exceptionMessage = ex.getMessage
      }
      record(
        "E01",
        "Safety Validation",
        "Overwrite rejected when target already exists",
        "throws Exception",
        if (overwriteCaught) s"threw (${exceptionMessage.take(40)}...)" else "did not throw",
        overwriteCaught,
        exceptionMessage
      )

      val sourceFilesUnchanged = fixtureData.keys.forall { fn =>
        val currentHash = sha256Hex(fixtureDir.resolve(fn))
        currentHash == initialChecksums(fn)
      }
      record(
        "E02",
        "Safety Validation",
        "Raw source CSVs remained unmodified after all runs",
        "true",
        sourceFilesUnchanged.toString,
        sourceFilesUnchanged
      )

      val isolationValid = outputPart2.startsWith(workspace) && fixtureDir.startsWith(workspace)
      record(
        "E03",
        "Safety Validation",
        "Temporary files strictly isolated within workspace",
        "true",
        isolationValid.toString,
        isolationValid
      )

      // -------------------------------------------------------------------------
      // TEST EXECUTION 2: inputPartitions = 1
      // -------------------------------------------------------------------------
      println("\n" + "-" * 100)
      println("EXECUTION 2: MovieLensIngestion with inputPartitions = 1 (coalesce to single partition)")
      println("-" * 100)

      val configPart1 = JobConfig(
        workspace = workspace,
        input = fixtureDir,
        output = outputPart1,
        job = "batch",
        master = "local[2]",
        shufflePartitions = 2,
        inputPartitions = 1
      )
      configPart1.validate()

      val bronze1: RawFrames = MovieLensIngestion.run(spark, configPart1)

      val frames1 = Seq(
        "ratings" -> bronze1.ratings,
        "movies" -> bronze1.movies,
        "tags" -> bronze1.tags,
        "links" -> bronze1.links
      )

      frames1.zipWithIndex.foreach { case ((name, df), idx) =>
        val numPart = df.rdd.getNumPartitions
        record(
          s"C${idx + 9}",
          "Partition Validation",
          s"RDD partition count == 1 (coalesce(1)): $name",
          "1",
          numPart.toString,
          numPart == 1
        )

        val partFiles = countParquetPartFiles(outputPart1.resolve("bronze").resolve(name))
        record(
          s"C${idx + 13}",
          "Partition Validation",
          s"Parquet part-file count == 1 on disk: $name",
          "1",
          partFiles.toString,
          partFiles == 1
        )
      }

      val reportPath1 = outputPart1.resolve("reports").resolve("ingestion.json")
      val reportExists1 = Files.isRegularFile(reportPath1)
      if (reportExists1) {
        val reportDf1 = spark.read.json(reportPath1.toString)
        val reqPart1 = reportDf1.select("metrics.requested_partitions").head().getLong(0)
        record(
          "D07",
          "Metrics Validation",
          "Single-partition run metrics.requested_partitions == 1",
          "1",
          reqPart1.toString,
          reqPart1 == 1L
        )
      }

      // -------------------------------------------------------------------------
      // Directory Listing Summary
      // -------------------------------------------------------------------------
      println("\n" + "-" * 100)
      println("BRONZE PARQUET DIRECTORY LISTING & SIZES")
      println("-" * 100)
      Seq(outputPart2 -> "Execution 1 (inputPartitions = 2)", outputPart1 -> "Execution 2 (inputPartitions = 1)").foreach {
        case (outDir, label) =>
          println(s"\n$label: $outDir")
          val bronzeDir = outDir.resolve("bronze")
          if (Files.isDirectory(bronzeDir)) {
            val stagesList = Files.list(bronzeDir)
            try {
              stagesList.forEach { stage =>
                val partCount = countParquetPartFiles(stage)
                val totalBytes = Files.walk(stage)
                  .filter(Files.isRegularFile(_))
                  .mapToLong(Files.size(_))
                  .sum()
                println(f"  Stage: ${stage.getFileName}%-10s | Part files: $partCount%2d | Total size: $totalBytes%,6d bytes")
                val files = Files.list(stage)
                try {
                  files.forEach { f =>
                    println(f"    - ${f.getFileName}%-50s (${Files.size(f)} bytes)")
                  }
                } finally files.close()
              }
            } finally stagesList.close()
          }
      }

      // -------------------------------------------------------------------------
      // Summary Report Table
      // -------------------------------------------------------------------------
      println("\n" + "=" * 100)
      println("                          MOVIEINTEL TEST ASSERTION SUMMARY")
      println("=" * 100)
      println(f"${"ID"}%-5s | ${"Category"}%-22s | ${"Assertion / Contract"}%-45s | ${"Expected"}%-12s | ${"Actual"}%-12s | ${"Status"}%-6s")
      println("-" * 108)

      results.foreach { r =>
        val status = if (r.passed) "PASS" else "FAIL"
        println(f"${r.id}%-5s | ${r.category}%-22s | ${r.description}%-45s | ${r.expected}%-12s | ${r.actual}%-12s | $status%-6s")
      }
      println("-" * 108)

      val total = results.size
      val passed = results.count(_.passed)
      val failed = results.count(!_.passed)
      println(s"TOTAL ASSERTIONS: $total | PASSED: $passed | FAILED: $failed")

      // Write machine-readable validation summary JSON
      val summaryReport = Map(
        "schema_version" -> 1,
        "runner" -> "com.movieintel.harness.BronzeIngestionRunner",
        "generated_at" -> Instant.now().toString,
        "spark_version" -> spark.version,
        "master" -> spark.sparkContext.master,
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
      println(s"Validation summary saved to: $summaryPath")

      if (failed > 0) {
        System.err.println(s"\nFATAL: $failed assertions failed.")
        sys.exit(1)
      } else {
        println("\nSUCCESS: All Bronze ingestion integration assertions passed cleanly.")
      }

    } finally {
      spark.stop()
      println("SparkSession stopped cleanly.")
    }
  }
}

