package cinescope

import org.apache.spark.sql.{DataFrame,SparkSession}
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.ml.recommendation.{ALS,ALSModel}
import org.apache.spark.ml.evaluation.RegressionEvaluator

/** Explicit-feedback ALS with per-user temporal train/validation/test partitions. */
object ALSRecommender {
  def main(args:Array[String]):Unit={
    require(args.length==2,"Usage: ALSRecommender <ratings.csv> <output>")
    val spark=SparkSession.builder.appName("CineScope temporal ALS").getOrCreate()
    import spark.implicits._
    val schema=new StructType().add("userId",IntegerType).add("movieId",IntegerType).add("rating",DoubleType).add("timestamp",LongType)
    val raw=spark.read.option("header",true).schema(schema).csv(args(0)).na.drop()
      .filter(col("rating").between(0.5,5.0))
    val order=Window.partitionBy("userId").orderBy("timestamp","movieId")
    val users=Window.partitionBy("userId")
    val ordered=raw.withColumn("rn",row_number.over(order)).withColumn("n",count(lit(1)).over(users)).filter(col("n")>=5)
    val train=ordered.filter(col("rn")<=floor(col("n")*.8)).select("userId","movieId","rating","timestamp").cache()
    val valid=ordered.filter(col("rn")>floor(col("n")*.8) && col("rn")<=floor(col("n")*.9)).cache()
    val test=ordered.filter(col("rn")>floor(col("n")*.9)).cache()
    val rmse=new RegressionEvaluator().setLabelCol("rating").setMetricName("rmse")
    def fit(rank:Int,reg:Double):ALSModel=new ALS().setUserCol("userId").setItemCol("movieId").setRatingCol("rating")
      .setRank(rank).setRegParam(reg).setMaxIter(12).setSeed(42).setColdStartStrategy("drop").fit(train)
    val trials=for(rank<-Seq(16,32);reg<-Seq(.05,.1))yield{
      val model=fit(rank,reg);val p=model.transform(valid)
      (if(p.take(1).isEmpty)Double.PositiveInfinity else rmse.evaluate(p),rank,reg,model)
    }
    val (validRMSE,bestRank,bestReg,best)=trials.minBy(_._1)
    require(!validRMSE.isInfinity,"No evaluable validation interactions")
    val predicted=best.transform(test).cache()
    val total=test.count();val scored=predicted.count()
    require(scored>0,"No evaluable test interactions")
    Seq(("validation_rmse",validRMSE),("test_rmse",rmse.evaluate(predicted)),
      ("test_coverage",scored.toDouble/total),("rank",bestRank.toDouble),("reg_param",bestReg))
      .toDF("metric","value").write.mode("overwrite").json(s"${args(1)}/metrics")
    best.write.overwrite().save(s"${args(1)}/model")
    best.itemFactors.write.mode("overwrite").parquet(s"${args(1)}/item_factors")
    // Top candidates: exclude TRAIN items before taking ten. Evaluated model stays train-only.
    val candidates=best.recommendForAllUsers(100).select(col("userId"),explode(col("recommendations")).as("rec"))
      .select(col("userId"),col("rec.movieId").as("movieId"),col("rec.rating").as("score"))
      .join(train.select("userId","movieId"),Seq("userId","movieId"),"left_anti")
    val ranked=candidates.withColumn("rank",row_number.over(Window.partitionBy("userId").orderBy(desc("score"),asc("movieId"))))
      .filter(col("rank")<=10)
    ranked.write.mode("overwrite").parquet(s"${args(1)}/ranked_candidates")
    test.select("userId","movieId","rating").write.mode("overwrite").parquet(s"${args(1)}/test_interactions")
    train.write.mode("overwrite").parquet(s"${args(1)}/train_interactions")
    // Recall/NDCG are computed in notebook 05; report the 100-candidate truncation explicitly.
    predicted.unpersist();train.unpersist();valid.unpersist();test.unpersist();spark.stop()
  }
}
