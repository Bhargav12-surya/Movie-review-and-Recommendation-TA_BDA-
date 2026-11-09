package com.movieintel.recommendation

import org.apache.spark.ml.recommendation.ALSModel
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._

/** Reproducible sampled ranking, with all positives and explicit cold fallback. */
object RankingEvaluation {
  def evaluate(model: ALSModel, train: DataFrame, heldout: DataFrame, k: Int,
      maximumUsers: Int = 100, negativesPerUser: Int = 100, seed: Long = 42L): DataFrame = {
    require(k >= 1 && k <= 100 && maximumUsers >= 1 && maximumUsers <= 1000 &&
      negativesPerUser >= k && negativesPerUser <= 1000, "Bound the declared sampled evaluation.")
    val positives = heldout.filter(col("rating") >= 4.0).select("userId", "movieId").distinct()
      .join(train.select("userId", "movieId").distinct(), Seq("userId", "movieId"), "left_anti")
    val users = positives.select("userId").distinct().orderBy(xxhash64(col("userId"), lit(seed)), col("userId")).limit(maximumUsers)
    require(users.limit(1).count() > 0, "No users with eligible held-out positives.")
    val truth = positives.join(users, Seq("userId"))
    val negativeUniverse = users.crossJoin(train.select("movieId").distinct())
      .join(train.select("userId", "movieId").distinct(), Seq("userId", "movieId"), "left_anti")
      .join(truth, Seq("userId", "movieId"), "left_anti")
    val sampling = Window.partitionBy("userId").orderBy(xxhash64(col("userId"), col("movieId"), lit(seed)), col("movieId"))
    val negatives = negativeUniverse.withColumn("sampleOrder", row_number().over(sampling))
      .filter(col("sampleOrder") <= negativesPerUser).select("userId", "movieId")
    val candidates = truth.withColumn("relevant", lit(1)).unionByName(negatives.withColumn("relevant", lit(0)))
    val popularity = train.groupBy("movieId").agg(count(lit(1)).as("trainingPopularity"))
    val predicted = model.transform(candidates).join(popularity, Seq("movieId"), "left")
      .na.fill(0L, Seq("trainingPopularity"))
      .withColumn("cold", col("prediction").isNull || isnan(col("prediction")))
      .withColumn("rankScore", when(col("cold"), log1p(col("trainingPopularity"))).otherwise(col("prediction")))
    // Fallback is explicit. Its raw popularity scale is disclosed; tune a serving
    // normalizer separately, rather than silently dropping cold candidates.
    val ordering = Window.partitionBy("userId").orderBy(col("rankScore").desc, col("movieId"))
    val ranked = predicted.withColumn("position", row_number().over(ordering))
      .withColumn("discountedHit", when(col("position") <= k, col("relevant") / (log(col("position") + 1) / log(lit(2.0)))).otherwise(0.0))
    val ideal = udf((n: Long) => (1 to math.min(k, n.toInt)).map(i => 1.0 / (math.log(i + 1) / math.log(2))).sum)
    ranked.groupBy("userId").agg(sum(col("relevant")).as("positiveCount"),
      sum(when(col("position") <= k, col("relevant")).otherwise(0)).as("hits"),
      sum(col("discountedHit")).as("dcg"), sum(when(col("cold"), 1).otherwise(0)).as("coldCandidates"),
      count(lit(1)).as("candidateCount"),
      collect_list(when(col("position") <= k, struct(col("position"), col("movieId"), col("relevant"), col("cold")))).as("topK"))
      .withColumn("precisionAtK", col("hits") / lit(k.toDouble))
      .withColumn("recallAtK", col("hits") / col("positiveCount"))
      .withColumn("ndcgAtK", col("dcg") / ideal(col("positiveCount")))
      .withColumn("candidateProtocol", lit("all_eligible_positives_plus_hash_sampled_train_items_after_seen_exclusion"))
      .withColumn("k", lit(k)).withColumn("negativesPerUser", lit(negativesPerUser))
  }
}
