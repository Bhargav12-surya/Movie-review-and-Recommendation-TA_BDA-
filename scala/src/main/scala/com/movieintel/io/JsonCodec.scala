package com.movieintel.io

/** Metadata only: dataframes are written through Spark, never collected here. */
object JsonCodec {
  def encode(value: Any): String = value match {
    case null => "null"
    case None => "null"
    case Some(item) => encode(item)
    case text: String => "\"" + text.flatMap {
      case '"' => "\\\""
      case '\\' => "\\\\"
      case '\n' => "\\n"
      case '\r' => "\\r"
      case '\t' => "\\t"
      case character if character < ' ' => "\\u" + "%04x".format(character.toInt)
      case character => character.toString
    } + "\""
    case item: Boolean => item.toString
    case item: Int => item.toString
    case item: Long => item.toString
    case item: Double =>
      require(!item.isNaN && !item.isInfinity, "Nonfinite JSON metadata.")
      item.toString
    case item: Float =>
      require(!item.isNaN && !item.isInfinity, "Nonfinite JSON metadata.")
      item.toString
    case entries: scala.collection.Map[_, _] =>
      entries.toSeq.sortBy(_._1.toString).map { case (key, item) =>
        encode(key.toString) + ":" + encode(item)
      }.mkString("{", ",", "}")
    case entries: Iterable[_] => entries.iterator.map(encode).mkString("[", ",", "]")
    case entries: Array[_] => entries.iterator.map(encode).mkString("[", ",", "]")
    case item => encode(item.toString)
  }
}
