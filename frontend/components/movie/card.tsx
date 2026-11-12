"use client";
import Link from "next/link";
import {useState} from "react";
import {posterURL} from "@/lib/api";
import type {Movie} from "@/lib/types";
import {ArrowIcon, SparkIcon, StarIcon} from "@/components/ui/icons";

export function Poster({movie, large = false}: {movie: Movie; large?: boolean}) {
  const [failed, setFailed] = useState(false);
  const url = posterURL(movie.poster_url);

  return (
    <div className={`poster ${large ? "large" : ""}`}>
      {url && !failed ? (
        <img
          src={url}
          alt={`Poster for ${movie.title}`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="poster-placeholder">
          <SparkIcon size={28} />
          <span>{movie.release_date?.slice(0, 4) ?? "Film"}</span>
          <strong>{movie.title}</strong>
        </div>
      )}
    </div>
  );
}

export function MovieCard({
  movie,
  badge,
  reason,
}: {
  movie: Movie;
  badge?: string;
  reason?: string;
}) {
  return (
    <article className="movie-card">
      <Link href={`/movies/${movie.id}`} className="poster-button" aria-label={`Explore ${movie.title}`}>
        <Poster movie={movie} />
        <span className="poster-hover">
          Explore film <ArrowIcon size={14} />
        </span>
        {badge && (
          <span className="rated-badge">
            <StarIcon size={12} />
            {badge}
          </span>
        )}
      </Link>
      <Link href={`/movies/${movie.id}`} className="movie-title">
        {movie.title}
      </Link>
      <div className="movie-meta">
        {movie.release_date?.slice(0, 4) ?? "—"} <span>·</span>{" "}
        {movie.genres.slice(0, 2).join(" / ") || "—"}
      </div>
      {reason && <p className="match-reason">{reason}</p>}
    </article>
  );
}

export function MovieGrid({movies}: {movies: Movie[]}) {
  return (
    <div className="movie-grid">
      {movies.map((movie) => (
        <MovieCard key={movie.id} movie={movie} />
      ))}
    </div>
  );
}
