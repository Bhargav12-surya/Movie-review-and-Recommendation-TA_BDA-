package cinescope

import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.Path
import org.apache.hadoop.io.{IntWritable,LongWritable,Text}
import org.apache.hadoop.mapreduce.{Job,Mapper,Reducer}
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat
import scala.collection.JavaConverters._

/** Actual Hadoop Mapper/Reducer job over review text, for BDA Unit 1. */
class ReviewWordMapper extends Mapper[LongWritable,Text,Text,IntWritable] {
  private val one=new IntWritable(1)
  override def map(key:LongWritable,value:Text,context:Mapper[LongWritable,Text,Text,IntWritable]#Context):Unit={
    value.toString.toLowerCase.split("[^a-z]+").filter(_.nonEmpty).foreach(t=>context.write(new Text(t),one))
  }
}
class ReviewWordReducer extends Reducer[Text,IntWritable,Text,IntWritable] {
  override def reduce(key:Text,values:java.lang.Iterable[IntWritable],context:Reducer[Text,IntWritable,Text,IntWritable]#Context):Unit={
    context.write(key,new IntWritable(values.asScala.map(_.get()).sum))
  }
}
object HadoopWordCount {
  def main(args:Array[String]):Unit={
    require(args.length==2,"Usage: HadoopWordCount <input-text> <output-directory>")
    val job=Job.getInstance(new Configuration(),"CineScope review word count")
    job.setJarByClass(classOf[ReviewWordMapper]);job.setMapperClass(classOf[ReviewWordMapper])
    job.setCombinerClass(classOf[ReviewWordReducer]);job.setReducerClass(classOf[ReviewWordReducer])
    job.setOutputKeyClass(classOf[Text]);job.setOutputValueClass(classOf[IntWritable])
    FileInputFormat.addInputPath(job,new Path(args(0)));FileOutputFormat.setOutputPath(job,new Path(args(1)))
    System.exit(if(job.waitForCompletion(true))0 else 1)
  }
}
