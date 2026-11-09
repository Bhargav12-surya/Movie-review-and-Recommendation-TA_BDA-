package com.movieintel.config

import java.nio.file.{Files, LinkOption, Path}
import scala.collection.mutable.ArrayBuffer

/** Resolve existing junctions before permitting any new local write. */
object PathPolicy {
  def resolved(path: Path): Path = {
    val absolute = path.toAbsolutePath.normalize()
    val tail = ArrayBuffer.empty[String]
    var ancestor = absolute
    while (!Files.exists(ancestor, LinkOption.NOFOLLOW_LINKS)) {
      require(ancestor.getParent != null, "No existing ancestor for path.")
      tail += ancestor.getFileName.toString
      ancestor = ancestor.getParent
    }
    tail.reverse.foldLeft(ancestor.toRealPath())((base, item) => base.resolve(item)).normalize()
  }

  def input(workspace: Path, path: Path): Path = {
    val root = workspace.toRealPath()
    val target = resolved(path)
    require(target.startsWith(root), "Input must stay inside the selected workspace.")
    require(Files.isDirectory(target), "Input directory does not exist.")
    require(!target.startsWith(resolved(root.resolve("temp"))),
      "Legacy demonstration data is not a Phase 2 source.")
    target
  }

  def output(workspace: Path, path: Path): Path = {
    val root = workspace.toRealPath()
    val target = resolved(path)
    require(target != root && target.startsWith(root), "Output must stay inside the workspace.")
    Seq("data/raw", "temp", ".git", ".venv", "models").foreach { relative =>
      val protectedPath = resolved(root.resolve(relative))
      require(target != protectedPath && !target.startsWith(protectedPath),
        s"Output cannot be written under protected path: $relative")
    }
    val iterator = root.relativize(target).iterator()
    while (iterator.hasNext) {
      require(!Set(".git", ".venv", "node_modules").contains(
        iterator.next().toString.toLowerCase(java.util.Locale.ROOT)),
        "Output cannot be written inside a dependency or Git directory.")
    }
    target
  }

  def child(workspace: Path, root: Path, relative: String): Path = {
    val part = root.getFileSystem.getPath(relative)
    require(relative.nonEmpty && !part.isAbsolute, "A relative output name is required.")
    val target = output(workspace, root.resolve(part))
    require(target.startsWith(resolved(root)) && target != resolved(root),
      "Output child must remain below its run root.")
    target
  }

  def createNew(workspace: Path, path: Path): Path = {
    val target = output(workspace, path)
    require(!Files.exists(target), "Output exists; choose a new run directory.")
    Files.createDirectories(target.getParent)
    Files.createDirectory(target)
  }

  /** Separate approved-model writer; ordinary ETL must never write model storage. */
  def newRecommendationModel(workspace: Path, path: Path): Path = {
    val root = workspace.toRealPath()
    val target = resolved(path)
    val modelRoot = resolved(root.resolve("models/recommendation"))
    require(modelRoot == root.resolve("models/recommendation"),
      "Model storage must not redirect through a junction to another project location.")
    require(target.startsWith(root) && target.startsWith(modelRoot) && target != modelRoot,
      "ALS models require a fresh child of workspace models/recommendation.")
    refuseProtectedSegments(target)
    require(!Files.exists(target), "Model output exists; overwrite is forbidden.")
    target
  }

  def refuseProtectedSegments(path: Path): Unit = {
    val elements = ArrayBuffer.empty[String]
    val iterator = path.toAbsolutePath.normalize().iterator()
    while (iterator.hasNext) elements += iterator.next().toString.toLowerCase(java.util.Locale.ROOT)
    require(!elements.exists(Set(".git", ".venv", "node_modules")), "Protected directory.")
    require(!elements.sliding(2).exists(parts => parts == Seq("data", "raw")),
      "Raw datasets cannot be overwritten.")
  }
}
