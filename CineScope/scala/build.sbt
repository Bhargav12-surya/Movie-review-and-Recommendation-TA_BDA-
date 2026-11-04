ThisBuild / scalaVersion := "2.12.18"
ThisBuild / organization := "edu.cinescope"
ThisBuild / version := "1.0.0"
name := "cinescope-spark"
val sparkVersion = "3.5.7"
libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-core" % sparkVersion % "provided",
  "org.apache.spark" %% "spark-sql" % sparkVersion % "provided",
  "org.apache.spark" %% "spark-mllib" % sparkVersion % "provided",
  "org.apache.hadoop" % "hadoop-mapreduce-client-core" % "3.3.4" % "provided"
)
Compile / scalacOptions ++= Seq("-deprecation", "-feature", "-unchecked")
