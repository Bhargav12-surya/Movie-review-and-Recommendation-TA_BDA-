package com.movieintel.ingestion

import com.movieintel.config.Schemas
import org.apache.spark.sql.{Column, DataFrame}
import org.apache.spark.sql.functions._

final case class ValidatedEvents(accepted: DataFrame, rejected: DataFrame)

/** Producer attestations are mandatory, but do not replace Phase 9 DB ownership checks.
  * This event contract carries analysis, never raw private review text.
  */
object ReviewIngestion {
  private def present(column: String): Column =
    col(column).isNotNull && col(column).rlike("^[A-Za-z0-9][A-Za-z0-9:_-]{0,127}$")

  private def probability(column: String): Column =
    col(column).isNotNull && !isnan(col(column)) && col(column).between(0.0, 1.0)

  def validate(events: DataFrame, allowSynthetic: Boolean): ValidatedEvents = {
    require(Schemas.ReviewEvents.fieldNames.forall(events.columns.contains),
      "Use the explicit review event schema, including corrupt-record capture.")
    val fields = Schemas.ReviewEvents.fieldNames.filterNot(_ == "_corrupt_record")
    val base = events.withColumn("event_timestamp", expr("try_to_timestamp(event_time)"))
      .withColumn("payload_hash", sha2(to_json(struct(fields.map(col): _*),
        Map("ignoreNullFields" -> "false")), 256))
      .withColumn("semantic_hash", sha2(to_json(struct(fields.filterNot(_ == "event_id").map(col): _*),
        Map("ignoreNullFields" -> "false")), 256))
    val validProbabilities = probability("positive_probability") && probability("neutral_probability") &&
      probability("negative_probability") && abs(col("positive_probability") + col("neutral_probability") +
        col("negative_probability") - lit(1.0)) <= 0.000001
    val invalidOptionalProbability = Seq("positive_probability", "neutral_probability", "negative_probability")
      .map(name => col(name).isNotNull && !probability(name)).reduce(_ || _)
    val reason = when(col("_corrupt_record").isNotNull, lit("malformed_json_or_field_type"))
      .when(!coalesce(present("event_id") && present("review_id") && present("movie_id"), lit(false)),
        lit("invalid_identifiers"))
      .when(!coalesce(col("review_revision") >= 1L, lit(false)), lit("invalid_revision"))
      .when(!coalesce(col("operation").isin("upsert", "delete"), lit(false)), lit("invalid_operation"))
      .when(!coalesce(col("event_time").rlike(
        "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,9})?Z$") &&
        col("event_timestamp").isNotNull, lit(false)), lit("invalid_utc_event_time"))
      .when(col("event_timestamp") > expr("current_timestamp() + INTERVAL 5 MINUTES"), lit("future_event"))
      .when(!coalesce(col("canonical_movie_validated"), lit(false)), lit("unvalidated_canonical_movie"))
      .when(col("is_synthetic").isNull || (!lit(allowSynthetic) && col("is_synthetic")),
        lit("synthetic_or_unlabelled_source"))
      .when(invalidOptionalProbability, lit("invalid_optional_probability"))
      // Withdrawals still delete a formerly eligible record. Upserts need all eligibility.
      .when(col("operation") === "upsert" &&
        (col("consent_eligible").isNull || col("moderation_eligible").isNull), lit("missing_eligibility_flags"))
      .when(col("operation") === "upsert" && col("consent_eligible") && col("moderation_eligible") &&
        !coalesce(validProbabilities, lit(false)),
        lit("invalid_sentiment_probabilities"))
      .when(col("operation") === "upsert" && col("consent_eligible") && col("moderation_eligible") &&
        !coalesce(present("model_version"), lit(false)),
        lit("missing_model_version"))
      .otherwise(lit(null).cast("string"))
    val marked = base.withColumn("rejection_reason", reason)
    ValidatedEvents(marked.filter(col("rejection_reason").isNull).drop("rejection_reason"),
      marked.filter(col("rejection_reason").isNotNull))
  }
}
