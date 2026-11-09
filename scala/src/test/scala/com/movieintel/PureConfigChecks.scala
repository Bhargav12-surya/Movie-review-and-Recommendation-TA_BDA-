package com.movieintel

import com.movieintel.config.{JobConfig, PathPolicy}
import com.movieintel.io.JsonCodec
import java.nio.file.{Files, Paths}

/** Executable with ONLY Scala/JDK cached jars; this does not test Spark APIs. */
object PureConfigChecks {
  def main(args: Array[String]): Unit = {
    require(args.length == 1, "Supply a fresh test workspace.")
    val root = Paths.get(args(0)).toRealPath()
    var passed = 0
    def check(name: String)(body: => Unit): Unit = {
      body; passed += 1; println("PASS " + name)
    }
    def rejects(body: => Any): Unit = {
      var failed = false
      try body catch { case _: IllegalArgumentException => failed = true }
      assert(failed, "Expected an explicit validation refusal.")
    }
    Files.createDirectories(root.resolve("data/raw/fixture"))
    Files.createDirectories(root.resolve("data/events/fixture"))
    val output = root.resolve("data/processed/run-1")
    val base = JobConfig(root, root.resolve("data/raw/fixture"), output)
    check("bounded batch config") { base.validate() }
    check("raw output protected") { rejects(PathPolicy.output(root, root.resolve("data/raw/new"))) }
    check("workspace output protected") { rejects(PathPolicy.output(root, root)) }
    check("escape protected") { rejects(PathPolicy.output(root, root.resolve("../escape"))) }
    check("legacy output protected") { rejects(PathPolicy.output(root, root.resolve("temp/new"))) }
    check("ordinary ETL model output protected") { rejects(PathPolicy.output(root, root.resolve("models/new"))) }
    check("approved ALS model path") {
      assert(PathPolicy.newRecommendationModel(root, root.resolve("models/recommendation/run-1")) ==
        root.resolve("models/recommendation/run-1"))
    }
    check("ALS cannot write arbitrary output") {
      rejects(PathPolicy.newRecommendationModel(root, root.resolve("data/processed/run-1")))
    }
    check("dependency output protected") { rejects(PathPolicy.output(root, root.resolve("x/node_modules/new"))) }
    check("output child traversal protected") { rejects(PathPolicy.child(root, output, "../escape")) }
    check("bounded local threads") { rejects(base.copy(master = "local[*]").validate()) }
    check("bounded partitions") { rejects(base.copy(shufflePartitions = 129).validate()) }
    check("resume batch rejected") { rejects(base.copy(resume = true).validate()) }
    check("stream paths required") { rejects(base.copy(job = "stream").validate()) }
    val stream = base.copy(job = "stream", eventInput = Some(root.resolve("data/events/fixture")),
      checkpoint = Some(root.resolve("data/checkpoints/fixture")))
    check("separate stream paths") { stream.validate() }
    check("stream resume requires retained directories") { rejects(stream.copy(resume = true).validate()) }
    check("nested checkpoint rejected") { rejects(stream.copy(checkpoint = Some(output.resolve("cp"))).validate()) }
    check("bounded UI hold") { rejects(base.copy(holdUiSeconds = 3601).validate()) }
    check("invalid watermark rejected") { rejects(stream.copy(watermark = "-1 hours").validate()) }
    check("strict CLI unknown flag") { rejects(JobConfig.parse(Array("--workspace", root.toString, "--wat", "x"))) }
    check("strict CLI duplicate") { rejects(JobConfig.parse(Array("--output", "a", "--output", "b"))) }
    check("strict CLI missing output") { rejects(JobConfig.parse(Array("--workspace", root.toString))) }
    check("fresh output creation") { assert(PathPolicy.createNew(root, output) == output) }
    check("existing output rejected") { rejects(base.validate()) }
    check("exclusive output creation") { rejects(PathPolicy.createNew(root, output)) }
    check("valid CLI smoke") {
      assert(JobConfig.parse(Array("--workspace", root.toString, "--output", "smoke", "--job", "smoke")).job == "smoke")
    }
    check("JSON escaping and stable keys") {
      assert(JsonCodec.encode(Map("b" -> "a\n\"\\", "a" -> Seq(1, true, None))) ==
        "{\"a\":[1,true,null],\"b\":\"a\\n\\\"\\\\\"}")
    }
    check("JSON nonfinite rejected") { rejects(JsonCodec.encode(Double.NaN)) }
    println("PURE_SCALA_CHECKS_PASSED=" + passed)
  }
}
