package com.movieintel.io

import com.movieintel.config.PathPolicy
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path, Paths, StandardOpenOption}
import java.time.Instant
import org.apache.spark.sql.DataFrame

object PipelineIO {
  private def checked(frame: DataFrame, path: String): String = {
    val root = Paths.get(frame.sparkSession.conf.getOption("spark.movieintel.workspace")
      .getOrElse(System.getProperty("user.dir"))).toRealPath()
    val target = PathPolicy.output(root, Paths.get(path))
    require(!Files.exists(target), "Dataset output exists; overwrite is forbidden.")
    Files.createDirectories(target.getParent)
    target.toString
  }
  def writeParquet(frame: DataFrame, path: String, partitionColumns: Seq[String] = Seq.empty): Unit = {
    val target = checked(frame, path)
    val writer = frame.write.mode("errorifexists")
    if (partitionColumns.nonEmpty) writer.partitionBy(partitionColumns: _*).parquet(target)
    else writer.parquet(target)
  }
  def writeJson(frame: DataFrame, path: String): Unit =
    frame.write.mode("errorifexists").json(checked(frame, path))
  def writeText(path: Path, text: String): Unit = {
    val target = PathPolicy.resolved(path)
    PathPolicy.refuseProtectedSegments(target)
    Files.createDirectories(target.getParent)
    Files.write(target, text.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW,
      StandardOpenOption.WRITE)
    ()
  }
  def recordMetrics(output: Path, name: String, metrics: Map[String, Long]): Unit = {
    require(name.matches("[A-Za-z0-9_-]+"), "Invalid metrics name.")
    writeText(output.resolve("reports").resolve(s"$name.json"),
      JsonCodec.encode(Map("schema_version" -> 1, "generated_at" -> Instant.now.toString,
        "metrics" -> metrics)) + "\n")
  }
}
