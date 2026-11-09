package com.movieintel.recommendation

import com.movieintel.config.PathPolicy
import java.nio.file.{Files, Path}
import org.apache.spark.ml.recommendation.{ALS, ALSModel}
import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.IntegerType

final case class AlsParameters(rank: Int = 32, iterations: Int = 10,
    regularization: Double = 0.1, blocks: Int = 2, seed: Long = 42L) {
  require(rank >= 1 && rank <= 128, "ALS rank must be in 1..128.")
  require(iterations >= 1 && iterations <= 30, "ALS iterations must be in 1..30.")
  require(regularization > 0 && regularization.isFinite, "Positive finite regularization required.")
  require(blocks >= 1 && blocks <= 4, "Use 1..4 local ALS blocks.")
}

/** Phase 2 MLlib contract; fitting and temporal ranking evaluation are Phase 8.
  * MovieLens source IDs are NOT application account or canonical movie IDs.
  */
object AlsTraining {
  def prepareInput(trainingRatings: DataFrame): DataFrame = {
    require(Seq("userId", "movieId", "rating").forall(trainingRatings.columns.contains),
      "ALS input requires source userId, movieId, rating.")
    require(trainingRatings.schema("userId").dataType == IntegerType &&
      trainingRatings.schema("movieId").dataType == IntegerType,
      "MLlib ALS needs validated Int source IDs, not implicit truncation or app IDs.")
    val selected = trainingRatings.select("userId", "movieId", "rating")
    val invalid = selected.filter(col("userId").isNull || col("userId") <= 0 ||
      col("movieId").isNull || col("movieId") <= 0 || col("rating").isNull ||
      isnan(col("rating")) || !col("rating").between(0.5, 5.0) ||
      col("rating") * 2.0 =!= floor(col("rating") * 2.0))
    require(invalid.limit(1).count() == 0L, "Invalid ALS training record; run cleaning first.")
    require(selected.groupBy("userId", "movieId").count().filter(col("count") > 1)
      .limit(1).count() == 0L, "Duplicate ALS user/movie keys.")
    selected
  }

  def estimator(parameters: AlsParameters): ALS = new ALS()
    .setUserCol("userId").setItemCol("movieId").setRatingCol("rating")
    .setRank(parameters.rank).setMaxIter(parameters.iterations)
    .setRegParam(parameters.regularization).setSeed(parameters.seed)
    .setNumUserBlocks(parameters.blocks).setNumItemBlocks(parameters.blocks)
    .setImplicitPrefs(false).setColdStartStrategy("nan")

  def fitApproved(trainingRatings: DataFrame, parameters: AlsParameters,
      approvedRunId: String, workspace: Path, newModelDirectory: Path): ALSModel = {
    require(approvedRunId.matches("[A-Za-z0-9][A-Za-z0-9_-]{5,79}"),
      "A separately approved Phase 8 run identifier is required.")
    val target = PathPolicy.newRecommendationModel(workspace, newModelDirectory)
    require(!Files.exists(target), "Model output already exists.")
    // Caller must supply TRAIN ONLY from a verified temporal manifest. No default CLI calls fit.
    val model = estimator(parameters).fit(prepareInput(trainingRatings))
    model.write.save(target.toString)
    model
  }
}
