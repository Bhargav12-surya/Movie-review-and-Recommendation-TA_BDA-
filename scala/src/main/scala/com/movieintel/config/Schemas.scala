package com.movieintel.config

import org.apache.spark.sql.types._

object Schemas {
  private def raw(columns: String*): StructType =
    StructType((columns :+ "_corrupt_record").map(StructField(_, StringType, nullable = true)))
  val RatingsRaw: StructType = raw("userId", "movieId", "rating", "timestamp")
  val MoviesRaw: StructType = raw("movieId", "title", "genres")
  val TagsRaw: StructType = raw("userId", "movieId", "tag", "timestamp")
  val LinksRaw: StructType = raw("movieId", "imdbId", "tmdbId")
  val ReviewEvents: StructType = new StructType()
    .add("event_id", StringType).add("review_id", StringType)
    .add("review_revision", LongType).add("movie_id", StringType)
    .add("operation", StringType).add("event_time", StringType)
    .add("positive_probability", DoubleType).add("neutral_probability", DoubleType)
    .add("negative_probability", DoubleType).add("model_version", StringType)
    .add("canonical_movie_validated", BooleanType).add("consent_eligible", BooleanType)
    .add("moderation_eligible", BooleanType).add("is_synthetic", BooleanType)
    .add("_corrupt_record", StringType)
}
