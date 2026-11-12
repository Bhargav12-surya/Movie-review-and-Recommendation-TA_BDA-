"use client";
import {useEffect, useState, useCallback} from "react";
import {useParams} from "next/navigation";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {MovieDetail, Review} from "@/lib/types";
import {Poster, MovieGrid} from "@/components/movie/card";
import {AudienceScore, ScoreProfile} from "@/components/score/profile";
import {ReviewSummary} from "@/components/review/summary";
import {ReviewList} from "@/components/review/list";
import {ReviewComposer} from "@/components/review/composer";
import {RatingControl} from "@/components/movie/rating";
import {Loading, ErrorState} from "@/components/ui/states";
import {PlusIcon, ReviewIcon} from "@/components/ui/icons";

export default function MoviePage() {
  const {movieId} = useParams<{movieId: string}>();
  const auth = useAuth();
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [similar, setSimilar] = useState<MovieDetail[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reviewsError, setReviewsError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const reload = useCallback(() => setRefresh((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    setReviewsError("");
    api<MovieDetail>(`/movies/${movieId}`, {signal: controller.signal})
      .then(setMovie)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    api<{reviews: Review[]}>(`/movies/${movieId}/reviews`, {signal: controller.signal})
      .then((value) => setReviews(value.reviews))
      .catch((err) => {
        if (!controller.signal.aborted) setReviewsError(err.message);
      });
    api<{movies: MovieDetail[]}>(`/movies/${movieId}/similar`, {signal: controller.signal})
      .then((value) => setSimilar(value.movies))
      .catch(() => {});
    return () => controller.abort();
  }, [movieId, refresh]);

  async function save() {
    if (!auth.token) {
      setNotice("Sign in to save films to your watchlist.");
      return;
    }
    try {
      await api(`/me/watchlist/${movieId}`, {method: "PUT"}, auth.token);
      setNotice("Added to your watchlist.");
    } catch (err) {
      setNotice((err as Error).message);
    }
  }

  if (error) return <ErrorState message={error} retry={reload} />;
  if (!movie) return <Loading />;

  return (
    <>
      <section className="detail-hero">
        <Poster movie={movie} large />
        <div className="detail-info">
          <span className="eyebrow">IN FOCUS</span>
          <h1>{movie.title}</h1>
          <div className="detail-meta">
            <span>{movie.release_date?.slice(0, 4) ?? "—"}</span>
            <span>·</span>
            <span>{movie.runtime_minutes ? `${movie.runtime_minutes} min` : "—"}</span>
            <span>·</span>
            <span>{movie.genres.join(" / ") || "—"}</span>
          </div>

          {movie.genres.length > 0 && (
            <div className="tags">
              {movie.genres.map((genre) => (
                <span className="tag" key={genre}>
                  {genre}
                </span>
              ))}
              {movie.themes?.map((theme) => (
                <span className="tag theme" key={theme}>
                  {theme.replaceAll("_", " ")}
                </span>
              ))}
            </div>
          )}

          {movie.overview && <p>{movie.overview}</p>}

          <AudienceScore score={movie.scores.overall} />

          {movie.audience_star_rating?.count ? (
            <small style={{display: "block"}}>
              Member rating: {movie.audience_star_rating.mean?.toFixed(1)}/5 ·{" "}
              {movie.audience_star_rating.count} ratings
            </small>
          ) : null}

          <div className="actions">
            <button type="button" className="primary" onClick={save}>
              <PlusIcon size={15} /> Add to watchlist
            </button>
            <a className="secondary" href="#review-composer">
              <ReviewIcon size={15} /> Write a review
            </a>
          </div>
          {notice && (
            <p role="status" className="notice">
              {notice}
            </p>
          )}
        </div>
      </section>

      <div className="detail-columns">
        <div>
          <ReviewSummary summary={movie.summary} />
          {reviewsError ? (
            <ErrorState message={reviewsError} retry={reload} />
          ) : (
            <ReviewList reviews={reviews} />
          )}
          <div id="review-composer" style={{marginTop: 22}}>
            <ReviewComposer movieId={movieId} onComplete={reload} />
          </div>
        </div>

        <aside>
          <RatingControl movieId={movieId} onSaved={reload} />
          <ScoreProfile scores={movie.scores} />
        </aside>
      </div>

      {similar.length > 0 && (
        <section className="section">
          <div className="section-heading">
            <h2>Similar films</h2>
          </div>
          <MovieGrid movies={similar} />
        </section>
      )}
    </>
  );
}
