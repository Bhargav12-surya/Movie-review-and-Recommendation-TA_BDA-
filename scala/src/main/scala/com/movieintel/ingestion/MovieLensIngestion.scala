package com.movieintel.ingestion

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}

import com.movieintel.config.{JobConfig, Schemas}
import com.movieintel.io.PipelineIO
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.StructType

/** Raw string fields preserve evidence before explicit, non-throwing type checks. */
final case class RawFrames(
    ratings: DataFrame,
    movies: DataFrame,
    tags: DataFrame,
    links: DataFrame)

object MovieLensIngestion {
  private def checkHeader(path: Path, schema: StructType): Unit = {
    require(Files.isRegularFile(path) && !Files.isSymbolicLink(path),
      "Expected a regular local source file: " + path.getFileName)
    val reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)
    val header = new StringBuilder
    try {
      var value = reader.read()
      while (value != -1 && value != '\n' && value != '\r' && header.length < 1024) {
        header.append(value.toChar)
        value = reader.read()
      }
      require(header.length < 1024, "CSV header exceeds the bounded header limit.")
    } finally reader.close()
    val expected = schema.fieldNames.filterNot(_ == "_corrupt_record").mkString(",")
    require(header.toString.stripPrefix("\uFEFF") == expected,
      "CSV header does not match the explicit schema: " + path.getFileName)
  }

  private def readCsv(
      spark: SparkSession,
      root: Path,
      file: String,
      schema: StructType,
      multiline: Boolean): DataFrame = {
    val path = root.resolve(file)
    checkHeader(path, schema)
    spark.read
      .schema(schema)
      .option("header", "true")
      .option("enforceSchema", "true")
      .option("encoding", "UTF-8")
      .option("quote", "\"")
      .option("escape", "\"")
      .option("mode", "PERMISSIVE")
      .option("columnNameOfCorruptRecord", "_corrupt_record")
      .option("multiLine", multiline.toString)
      .option("ignoreLeadingWhiteSpace", "false")
      .option("ignoreTrailingWhiteSpace", "false")
      .csv(path.toString)
      .withColumn("_source_file", input_file_name())
      .withColumn("_source_name", lit("ml-32m"))
      .withColumn("_ingested_at", current_timestamp())
  }

  def read(spark: SparkSession, input: Path): RawFrames = RawFrames(
    readCsv(spark, input, "ratings.csv", Schemas.RatingsRaw, multiline = false),
    readCsv(spark, input, "movies.csv", Schemas.MoviesRaw, multiline = false),
    readCsv(spark, input, "tags.csv", Schemas.TagsRaw, multiline = true),
    readCsv(spark, input, "links.csv", Schemas.LinksRaw, multiline = false))

  def run(spark: SparkSession, config: JobConfig): RawFrames = {
    spark.conf.set("spark.movieintel.workspace", config.workspace.toString)
    val raw = read(spark, config.input)
    val frames = Seq("ratings" -> raw.ratings, "movies" -> raw.movies,
      "tags" -> raw.tags, "links" -> raw.links)
    frames.foreach { case (name, frame) =>
      PipelineIO.writeParquet(frame.coalesce(config.inputPartitions),
        config.stage("bronze", name))
    }
    // Read materialized Bronze rather than reparsing CSV on every later action.
    val bronze = RawFrames(
      spark.read.parquet(config.stage("bronze", "ratings")),
      spark.read.parquet(config.stage("bronze", "movies")),
      spark.read.parquet(config.stage("bronze", "tags")),
      spark.read.parquet(config.stage("bronze", "links")))
    PipelineIO.recordMetrics(config.output, "ingestion", Map(
      "ratings_rows" -> bronze.ratings.count(),
      "movies_rows" -> bronze.movies.count(),
      "tags_rows" -> bronze.tags.count(),
      "links_rows" -> bronze.links.count(),
      "requested_partitions" -> config.inputPartitions.toLong))
    bronze
  }
}
