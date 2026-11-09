package com.movieintel.analytics

import com.movieintel.cleaning.CleanFrames
import com.movieintel.config.JobConfig
import com.movieintel.io.PipelineIO
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._

/** Source-user statistics; MovieLens users never become application accounts. */
object UserAnalytics {
  def tables(clean: CleanFrames): Map[String, DataFrame] = {
    val users = clean.ratings.groupBy("userId", "source_user_key").agg(
      count(lit(1)).as("rating_count"), avg("rating").as("mean_star_rating"),
      min("timestamp").as("first_rating_timestamp"), max("timestamp").as("last_rating_timestamp"))
    val movieGenres = clean.movies.select(col("movieId"), explode(col("genreArray")).as("genre"))
    val genres = clean.ratings.join(movieGenres, Seq("movieId"), "inner")
      .groupBy("userId", "source_user_key", "genre").agg(
        count(lit(1)).as("genre_rating_count"),
        avg("rating").as("genre_mean_star_rating"))
      .join(users.select("userId", "mean_star_rating", "rating_count"), Seq("userId"), "inner")
      .withColumn("genre_rating_fraction", col("genre_rating_count").cast("double") / col("rating_count"))
      .withColumn("genre_mean_deviation", col("genre_mean_star_rating") - col("mean_star_rating"))
    val interests = clean.tags.groupBy("userId", "source_user_key", "tag").agg(
      count(lit(1)).as("tag_application_count"),
      countDistinct("movieId").as("tagged_movie_count"),
      max("timestamp").as("last_tag_timestamp"))
      .withColumn("log_tag_frequency", log1p(col("tag_application_count").cast("double")))
    Map("source_user_profiles" -> users,
      "source_user_genre_profiles" -> genres,
      "source_user_tag_interests" -> interests,
      "source_user_activity_yearly" -> clean.ratings.groupBy("userId", "source_user_key", "event_year")
        .agg(count(lit(1)).as("rating_count"), avg("rating").as("mean_star_rating")))
  }

  def run(spark: SparkSession, clean: CleanFrames, config: JobConfig): Map[String, Long] = {
    spark.conf.set("spark.movieintel.workspace", config.workspace.toString)
    val counts = tables(clean).toSeq.sortBy(_._1).map { case (name, frame) =>
      PipelineIO.writeParquet(frame, config.stage("gold", name))
      name + "_rows" -> spark.read.parquet(config.stage("gold", name)).count()
    }.toMap
    PipelineIO.recordMetrics(config.output, "user_analytics", counts)
    counts
  }
}
