ThisBuild / scalaVersion := "2.13.18"
ThisBuild / organization := "edu.movieintel"
ThisBuild / version := "0.1.0"

name := "movieintel-spark"
val sparkVersion = "4.3.0"

// Resolution is a MANUAL prerequisite step. Do not run SBT to bootstrap software.
libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-core" % sparkVersion % Provided,
  "org.apache.spark" %% "spark-sql" % sparkVersion % Provided,
  "org.apache.spark" %% "spark-mllib" % sparkVersion % Provided,
  "org.scalatest" %% "scalatest" % "3.2.19" % Test
)

Compile / scalacOptions ++= Seq("-deprecation", "-feature", "-unchecked", "-release", "17")
Compile / mainClass := Some("com.movieintel.Main")
Compile / packageOptions += Package.ManifestAttributes(
  "Spark-Version" -> sparkVersion, "Scala-Version" -> scalaVersion.value)
Test / fork := true
Test / parallelExecution := false
Test / javaOptions ++= Seq(
  "-Xms256m", "-Xmx1536m", "-Dspark.ui.enabled=false", "-Djava.net.preferIPv4Stack=true"
) ++ Seq(
  "java.base/java.lang", "java.base/java.lang.invoke", "java.base/java.lang.reflect",
  "java.base/java.io", "java.base/java.net", "java.base/java.nio", "java.base/java.util",
  "java.base/java.util.concurrent", "java.base/java.util.concurrent.atomic",
  "java.base/sun.nio.ch", "java.base/sun.nio.cs", "java.base/sun.security.action",
  "java.base/sun.util.calendar", "java.security.jgss/sun.security.krb5"
).map(module => s"--add-opens=$module=ALL-UNNAMED")

// Thin JAR: the manually installed matching Spark distribution supplies Spark.
Compile / packageBin / artifactPath :=
  baseDirectory.value / "target" / ("scala-" + scalaBinaryVersion.value) /
    (name.value + "_" + scalaBinaryVersion.value + "-" + version.value + ".jar")
