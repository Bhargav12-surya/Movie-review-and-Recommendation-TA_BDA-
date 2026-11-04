package cinescope

import scala.annotation.tailrec
import scala.collection.mutable
import scala.concurrent.{Await, ExecutionContext, Future}
import scala.concurrent.duration._

/** BDA Unit 2: FP, type hierarchy, closures, collections, OOP and concurrency. */
object FunctionalProgramming {
  case class Review(movieId: Int, text: String, rating: Double)
  trait ReviewRule { def accept(r: Review): Boolean }
  final class MinimumLength(minimum: Int) extends ReviewRule {
    override def accept(r: Review): Boolean = r.text.length >= minimum
  }
  sealed trait ConsList[+A]
  case object Empty extends ConsList[Nothing]
  case class Cons[A](head: A, tail: ConsList[A]) extends ConsList[A]
  @tailrec def length[A](xs: ConsList[A], acc: Int = 0): Int = xs match {
    case Empty => acc
    case Cons(_, tail) => length(tail, acc + 1)
  }
  // A closure captures a threshold; Review => Boolean is a first-class value.
  def above(threshold: Double): Review => Boolean = _.rating >= threshold
  def transform[A, B](rows: List[A])(f: A => B): List[B] = rows.map(f)

  def main(args: Array[String]): Unit = {
    val reviews = Vector(Review(1,"Excellent story",4.5), Review(2,"Slow pacing",2.0))
    val liked = reviews.filter(above(3.5)).map(_.movieId)
    val counts = reviews.groupBy(_.movieId).map { case (id, xs) => id -> xs.size }
    val updated = counts.updated(3, 1) // original counts remains immutable
    val mutableExample = mutable.Map.empty[Int, Int]
    reviews.foreach(r => mutableExample.update(r.movieId, mutableExample.getOrElse(r.movieId,0)+1))
    val rule: ReviewRule = new MinimumLength(5)
    val universal: Any = reviews // Any -> AnyRef for collections; Double extends AnyVal
    val cons: ConsList[Int] = Cons(1, Cons(2, Empty))
    implicit val ec: ExecutionContext = ExecutionContext.global
    // Futures demonstrate concurrency; Spark provides distributed execution separately.
    val validated = Future.sequence(reviews.map(r => Future(rule.accept(r))))
    println(s"liked=$liked counts=$counts updated=$updated consLength=${length(cons)}")
    println(Await.result(validated, 10.seconds))
    println(transform(reviews.toList)(_.text.toLowerCase))
  }
}
