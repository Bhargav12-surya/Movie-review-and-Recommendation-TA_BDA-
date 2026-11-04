package cinescope

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import org.apache.spark.ml.{Pipeline, PipelineModel}
import org.apache.spark.ml.feature._
import org.apache.spark.ml.classification.LogisticRegression
import org.apache.spark.ml.evaluation.{BinaryClassificationEvaluator, MulticlassClassificationEvaluator}

/** TF-IDF bigrams + MLlib Logistic Regression. Fit vocabulary/IDF on train only. */
object SentimentPipeline {
  def main(args: Array[String]): Unit = {
    require(args.length==2,"Usage: SentimentPipeline <imdb_reviews.jsonl> <output>")
    val spark=SparkSession.builder.appName("CineScope Sentiment Pipeline").getOrCreate()
    import spark.implicits._
    val rows=spark.read.json(args(0)).withColumn("label",col("label").cast("double"))
      .filter(col("text").isNotNull && col("label").isin(0.0,1.0))
    val trainPool=rows.filter(col("split")==="train")
      .withColumn("bucket",pmod(crc32(coalesce(col("imdb_id"),col("review_id"))),lit(100)))
    val train=trainPool.filter(col("bucket")<80).cache()
    val valid=trainPool.filter(col("bucket")>=80).cache()
    val test=rows.filter(col("split")==="test").cache()
    require(train.count()>0 && valid.count()>0 && test.count()>0,"Need nonempty train/validation/test")
    val tokenizer=new RegexTokenizer().setInputCol("text").setOutputCol("words").setPattern("[^a-zA-Z']+").setToLowercase(true)
    val stop=new StopWordsRemover().setInputCol("words").setOutputCol("filtered")
      .setStopWords(StopWordsRemover.loadDefaultStopWords("english").filterNot(Set("not","no","never","nor")))
    val bigrams=new NGram().setN(2).setInputCol("filtered").setOutputCol("bigrams")
    val combine=new SQLTransformer().setStatement("SELECT *, concat(filtered, bigrams) AS terms FROM __THIS__")
    val counts=new CountVectorizer().setInputCol("terms").setOutputCol("counts").setVocabSize(60000).setMinDF(2)
    val idf=new IDF().setInputCol("counts").setOutputCol("features")
    val f1=new MulticlassClassificationEvaluator().setMetricName("f1")
    val auc=new BinaryClassificationEvaluator().setMetricName("areaUnderROC")
    val trials=Seq(0.01,0.1).map { reg =>
      val lr=new LogisticRegression().setMaxIter(60).setRegParam(reg)
      val fitted=new Pipeline().setStages(Array(tokenizer,stop,bigrams,combine,counts,idf,lr)).fit(train)
      (f1.evaluate(fitted.transform(valid)),reg,fitted)
    }
    val (validationF1,bestReg,best)=trials.maxBy(_._1)
    val predictions=best.transform(test).cache()
    Seq(("validation_weighted_f1",validationF1),("test_weighted_f1",f1.evaluate(predictions)),
      ("test_roc_auc",auc.evaluate(predictions)),("selected_reg_param",bestReg))
      .toDF("metric","value").write.mode("overwrite").json(s"${args(1)}/metrics")
    predictions.groupBy("label","prediction").count().write.mode("overwrite").json(s"${args(1)}/confusion")
    best.write.overwrite().save(s"${args(1)}/model")
    train.unpersist();valid.unpersist();test.unpersist();predictions.unpersist();spark.stop()
  }
}
