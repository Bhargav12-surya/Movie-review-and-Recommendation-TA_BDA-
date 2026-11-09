package com.movieintel.config

import java.nio.file.{Files, Path, Paths}

final case class JobConfig(
    workspace: Path, input: Path, output: Path, job: String = "batch",
    master: String = "local[2]", shufflePartitions: Int = 8, inputPartitions: Int = 4,
    allowSyntheticEvents: Boolean = false, resume: Boolean = false,
    eventInput: Option[Path] = None, checkpoint: Option[Path] = None,
    watermark: String = "24 hours", maxFilesPerTrigger: Int = 5,
    availableNow: Boolean = true, holdUiSeconds: Int = 0
) {
  def stage(layer: String, name: String): String =
    PathPolicy.child(workspace, output, s"$layer/$name").toString

  def validate(): Unit = {
    require(Files.isDirectory(workspace), "Workspace is absent.")
    require(Set("batch", "rdd", "smoke", "stream").contains(job), "Unknown job.")
    require(master == "local" || master.matches("local\\[[1-4]\\]"),
      "Use bounded local execution: local or local[1] through local[4].")
    require(shufflePartitions >= 1 && shufflePartitions <= 128, "Invalid shuffle partition count.")
    require(inputPartitions >= 1 && inputPartitions <= 32, "Invalid input partition count.")
    require(maxFilesPerTrigger >= 1 && maxFilesPerTrigger <= 100, "Invalid file-trigger limit.")
    require(holdUiSeconds >= 0 && holdUiSeconds <= 3600, "Invalid Spark UI hold time.")
    require(watermark.matches("[1-9][0-9]* (seconds|minutes|hours|days)"),
      "Watermark must be a positive whole interval.")
    val out = PathPolicy.output(workspace, output)
    require(job == "stream" || !resume, "Resume is supported only for the event stream.")
    require(resume || !Files.exists(out), "Output exists; choose a fresh run directory.")
    if (job != "smoke" && job != "stream") {
      val in = PathPolicy.input(workspace, input)
      require(!out.startsWith(in) && !in.startsWith(out), "Input and output must not overlap.")
    }
    if (job == "stream") {
      require(eventInput.nonEmpty && checkpoint.nonEmpty, "Stream requires event input and checkpoint paths.")
      val events = PathPolicy.input(workspace, eventInput.get)
      val cp = PathPolicy.output(workspace, checkpoint.get)
      require(if (resume) Files.isDirectory(out) && Files.isDirectory(cp) else !Files.exists(cp),
        "A new stream needs a fresh checkpoint; resume needs retained output and checkpoint directories.")
      require(!out.startsWith(events) && !events.startsWith(out), "Event input and output must not overlap.")
      require(!cp.startsWith(events) && !events.startsWith(cp), "Checkpoint and event input must not overlap.")
      require(!cp.startsWith(out) && !out.startsWith(cp), "Checkpoint and output must be separate.")
    }
  }
}

object JobConfig {
  val usage: String =
    """Usage: --job batch|rdd|smoke|stream --workspace PATH --input PATH --output NEW_PATH
      |[--master local[2]] [--shuffle-partitions 8] [--input-partitions 4]
      |Stream: --event-input PATH --checkpoint PATH [--resume] [--allow-synthetic-events]
      |[--watermark "24 hours"] [--max-files-per-trigger 5] [--continuous]
      |[--hold-ui-seconds 0]""".stripMargin

  def parse(args: Array[String]): JobConfig = {
    val flags = Set("--resume", "--allow-synthetic-events", "--continuous")
    val values = Set("--job", "--workspace", "--input", "--output", "--master",
      "--shuffle-partitions", "--input-partitions", "--event-input", "--checkpoint",
      "--watermark", "--max-files-per-trigger", "--hold-ui-seconds")
    var options = Map.empty[String, String]
    var index = 0
    while (index < args.length) {
      val key = args(index)
      require((flags ++ values).contains(key), s"Unknown argument: $key\n$usage")
      require(!options.contains(key), s"Duplicate argument: $key")
      if (flags.contains(key)) {
        options += key -> "true"; index += 1
      } else {
        require(index + 1 < args.length && !args(index + 1).startsWith("--"), s"Missing value for $key")
        options += key -> args(index + 1); index += 2
      }
    }
    val root = Paths.get(options.getOrElse("--workspace", ".")).toAbsolutePath.normalize().toRealPath()
    def path(value: String): Path = {
      val supplied = Paths.get(value)
      (if (supplied.isAbsolute) supplied else root.resolve(supplied)).normalize()
    }
    val result = JobConfig(
      root, path(options.getOrElse("--input", "data/raw/movielens/ml-32m")),
      path(options.getOrElse("--output", throw new IllegalArgumentException("--output is required."))),
      options.getOrElse("--job", "batch"), options.getOrElse("--master", "local[2]"),
      options.getOrElse("--shuffle-partitions", "8").toInt,
      options.getOrElse("--input-partitions", "4").toInt,
      options.contains("--allow-synthetic-events"), options.contains("--resume"),
      options.get("--event-input").map(path), options.get("--checkpoint").map(path),
      options.getOrElse("--watermark", "24 hours"), options.getOrElse("--max-files-per-trigger", "5").toInt,
      !options.contains("--continuous"), options.getOrElse("--hold-ui-seconds", "0").toInt)
    result.validate()
    result
  }
}
