import Link from "next/link";
import type {Recommendation} from "@/lib/types";
import {Poster} from "@/components/movie/card";
import {ArrowIcon, SparkIcon} from "@/components/ui/icons";

export function RecommendationShelf({items}: {items: Recommendation[]}) {
  return (
    <div className="recommendation-grid">
      {items.map((row) => (
        <article className="movie-card" key={row.movie_id}>
          <Link
            href={`/movies/${row.movie_id}`}
            className="poster-button"
            aria-label={`Explore ${row.movie.title}`}
          >
            <Poster movie={row.movie} />
            <span className="poster-hover">
              Explore film <ArrowIcon size={14} />
            </span>
            <span className="rated-badge">
              <SparkIcon size={12} />
              {Math.round(row.match_score * 100)}% match
            </span>
          </Link>

          <Link href={`/movies/${row.movie_id}`} className="movie-title">
            {row.movie.title}
          </Link>

          <div className="movie-meta">
            {row.movie.release_date?.slice(0, 4) ?? "—"} <span>·</span>{" "}
            {row.movie.genres.slice(0, 2).join(" / ") || "—"}
          </div>

          {Object.entries(row.evidence)
            .filter(([name]) => name === "genre" || name === "theme")
            .map(([name, value]) => {
              const keys = Object.keys((value as Record<string, number>) ?? {});
              if (!keys.length) return null;
              return (
                <p className="match-reason" key={name}>
                  {keys.join(" + ")}
                </p>
              );
            })}
        </article>
      ))}
    </div>
  );
}
