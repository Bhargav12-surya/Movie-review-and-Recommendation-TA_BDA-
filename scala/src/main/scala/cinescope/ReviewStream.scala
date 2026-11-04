package cinescope

import org.apache.spark.sql.{DataFrame,SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.ml.PipelineModel

/** Durable file-source Structured Streaming; optional trained Spark sentiment pipeline. */
object ReviewStream {
  def main(args:Array[String]):Unit={
    require(args.length>=3,"Usage: ReviewStream <events-dir> <output-dir> <checkpoint-dir> [sentiment-model]")
    val spark=SparkSession.builder.appName("CineScope live review analytics").getOrCreate()
    val schema=new StructType().add("review_id",StringType).add("movie_id",IntegerType)
      .add("text",StringType).add("source",StringType).add("created_at",StringType)
    val source=spark.readStream.schema(schema).option("maxFilesPerTrigger",20).json(args(0))
      .withColumn("event_time",to_timestamp(col("created_at")))
      .filter(col("event_time").isNotNull && col("text").isNotNull)
      .withWatermark("event_time","24 hours").dropDuplicatesWithinWatermark("review_id")
    val predicted=if(args.length>3)PipelineModel.load(args(3)).transform(source) else source
    // Append sink + checkpoint allow Spark to commit batches consistently on restart.
    val query=predicted.withColumn("event_date",to_date(col("event_time"))).writeStream
      .format("parquet").outputMode("append").option("path",args(1))
      .option("checkpointLocation",args(2)).partitionBy("event_date").start()
    query.awaitTermination()
  }
}
