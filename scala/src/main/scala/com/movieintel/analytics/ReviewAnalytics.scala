package com.movieintel.analytics

import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

/** Shared Phase7 formula on already eligible, one-row-per-reviewer evidence.
  * Revision/consent/model/target contracts must be validated before this stage.
  * Does not substitute MovieLens star ratings for sentiment probabilities.
  */
object ReviewAnalytics {
  def aggregateEligible(
      input: DataFrame,
      minimumReviews: Int,
      minimumDistinct: Int,
      minimumEffective: Double,
      strength: Double,
      prior: Double
  ): DataFrame = {
    require(
      minimumReviews >= 1 && minimumDistinct >= 1 && minimumEffective >= 1 && minimumEffective.isFinite &&
        strength >= 0 && strength.isFinite && prior >= 0 && prior <= 100,
      "Reviewed finite scoring policy required."
    )
    val columns = Seq(
      "movie_id",
      "review_id",
      "reviewer_id",
      "p_negative",
      "p_neutral",
      "p_positive",
      "weight"
    )
    require(
      columns.forall(input.columns.contains),
      "Eligible score schema missing."
    )
    val invalid = input.filter(
      columns.map(name => col(name).isNull).reduce(_ || _) ||
        Seq("p_negative", "p_neutral", "p_positive", "weight")
          .map(name => isnan(col(name)) || !col(name).between(0.0, 1.0))
          .reduce(_ || _) ||
        abs(
          col("p_negative") + col("p_neutral") + col("p_positive") - 1.0
        ) > 1e-6
    )
    require(
      invalid.limit(1).count() == 0,
      "Invalid eligible probabilities or weights."
    )
    require(
      input
        .groupBy("movie_id", "reviewer_id")
        .count()
        .filter(col("count") > 1)
        .limit(1)
        .count() == 0,
      "One eligible review per reviewer per movie is required before aggregation."
    )
    require(
      input
        .groupBy("movie_id", "review_id")
        .count()
        .filter(col("count") > 1)
        .limit(1)
        .count() == 0,
      "Duplicate review identities must be reconciled before aggregation."
    )
    val active = input
      .filter(col("weight") > 0)
      .withColumn(
        "sentimentIndex",
        (col("p_positive") + col("p_neutral") * lit(0.5)) * lit(100.0)
      )
    val metrics = active
      .groupBy("movie_id")
      .agg(
        count(lit(1)).as("review_count"),
        countDistinct("reviewer_id").as("distinct_reviewers"),
        sum("weight").as("sum_weight"),
        sum(col("weight") * col("weight")).as("sum_squared_weight"),
        sum(col("weight") * col("sentimentIndex")).as("weighted_total")
      )
      .withColumn(
        "effective_review_count",
        col("sum_weight") * col("sum_weight") / col("sum_squared_weight")
      )
      .withColumn("raw_score", col("weighted_total") / col("sum_weight"))
    input
      .select("movie_id")
      .distinct()
      .join(metrics, Seq("movie_id"), "left")
      .na
      .fill(0L, Seq("review_count", "distinct_reviewers"))
      .na
      .fill(0.0, Seq("effective_review_count"))
      .withColumn(
        "enough",
        col("review_count") >= minimumReviews && col(
          "distinct_reviewers"
        ) >= minimumDistinct && col(
          "effective_review_count"
        ) >= minimumEffective
      )
      .withColumn(
        "score",
        when(
          col("enough"),
          (col("effective_review_count") * col(
            "raw_score"
          ) + strength * prior) / (col("effective_review_count") + strength)
        )
      )
      .withColumn(
        "raw_score",
        when(col("enough"), col("raw_score"))
          .otherwise(lit(null).cast("double"))
      )
      .withColumn(
        "message",
        when(!col("enough"), lit("Not enough audience reviews yet."))
          .otherwise(lit(null).cast("string"))
      )
  }
}
