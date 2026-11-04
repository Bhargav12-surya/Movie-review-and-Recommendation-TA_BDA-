import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

/** Usage: MovieStats <MovieLens folder> <new output folder>
  * Batch processing: no training and no Spark job per typed review.
  */
object MovieStats {
  def main(args: Array[String]): Unit = {
    require(args.length == 2, "Need MovieLens input folder and output folder")
    val spark = SparkSession.builder.appName("CineScope MovieLens Stats").getOrCreate()
    val ratingSchema = new StructType()
      .add("userId", IntegerType).add("movieId", IntegerType)
      .add("rating", DoubleType).add("timestamp", LongType)
    val movieSchema = new StructType()
      .add("movieId", IntegerType).add("title", StringType).add("genres", StringType)
    val ratings = spark.read.option("header", true).schema(ratingSchema)
      .csv(args(0) + "/ratings.csv")
      .na.drop(Seq("userId", "movieId", "rating", "timestamp"))
      .filter(col("rating").between(0.5, 5.0))
      .dropDuplicates("userId", "movieId", "rating", "timestamp")
    val movies = spark.read.option("header", true).schema(movieSchema)
      .csv(args(0) + "/movies.csv").na.drop(Seq("movieId", "title"))
      .dropDuplicates("movieId")
    val stats = ratings.groupBy("movieId").agg(
      count(lit(1)).as("rating_count"), avg("rating").as("mean_rating"))
    val joined = movies.join(stats, Seq("movieId"), "left")
      .na.fill(Map("rating_count" -> 0L, "mean_rating" -> 3.0))
    joined.write.mode("errorifexists").parquet(args(1) + "/movie_stats")
    joined.withColumn("genre", explode(split(col("genres"), "\\|")))
      .filter(col("genre") =!= "(no genres listed)")
      .groupBy("genre").agg(sum("rating_count").as("rating_events"),
        (sum(col("rating_count") * col("mean_rating")) / sum("rating_count")).as("mean_rating"))
      .write.mode("errorifexists").option("header", true).csv(args(1) + "/genre_stats")
    // A bounded export is for the small UI only. Full results stay distributed.
    joined.orderBy(desc("rating_count"), asc("movieId")).limit(2000)
      .select(concat(lit("ml:"),col("movieId")).as("id"), col("title"),
        split(col("genres"),"\\|").as("genres"), col("rating_count"), col("mean_rating"))
      .coalesce(1).write.mode("errorifexists").json(args(1) + "/ui_catalog")
    spark.stop()
  }
}
