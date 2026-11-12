"use client";
import {useEffect, useState, useCallback} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {Catalogue, MovieDetail, Review} from "@/lib/types";
import {ReviewSummary} from "@/components/review/summary";
import {ReviewList} from "@/components/review/list";
import {ReviewComposer} from "@/components/review/composer";
import {AudienceScore, ScoreProfile} from "@/components/score/profile";
import {Loading, ErrorState} from "@/components/ui/states";
import {SearchIcon} from "@/components/ui/icons";

export default function StudioPage() {
  const auth = useAuth();
  const [search, setSearch] = useState("");
  const [movies, setMovies] = useState<Catalogue["movies"]>([]);
  const [movieId, setMovieId] = useState("");
  const [detail, setDetail] = useState<MovieDetail | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [latestReview, setLatestReview] = useState<Review | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  const reload = useCallback(() => setRefresh((v) => v + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api<Catalogue>(
        `/movies?q=${encodeURIComponent(search.trim())}&page_size=25`,
        {signal: controller.signal},
      )
        .then((res) => {
          setMovies(res.movies);
          setMovieId((prev) =>
            prev && res.movies.some((m) => m.id === prev) ? prev : res.movies[0]?.id ?? prev,
          );
        })
        .catch((err) => {
          if (!controller.signal.aborted) setError(err.message);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [search]);

  useEffect(() => {
    if (!movieId) return;
    const controller = new AbortController();
    setError("");
    api<MovieDetail>(`/movies/${movieId}`, {signal: controller.signal})
      .then(setDetail)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    api<{reviews: Review[]}>(`/movies/${movieId}/reviews`, {signal: controller.signal})
      .then((res) => setReviews(res.reviews))
      .catch(() => {});
    return () => controller.abort();
  }, [movieId, refresh]);

  return (
    <>
      <header className="page-heading">
        <span className="eyebrow">BEYOND THE STARS</span>
        <h1>Every review has a story.</h1>
        <p>Write a review, inspect live worker analysis, and see what stood out.</p>
      </header>

      <div className="search-form" style={{marginBottom: 16}}>
        <SearchIcon size={18} />
        <label htmlFor="studio-movie-search" className="sr-only">
          Filter films
        </label>
        <input
          id="studio-movie-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search a film to review…"
          maxLength={200}
        />
      </div>

      {movies.length > 0 && (
        <div className="panel" style={{padding: "14px 18px", marginBottom: 18}}>
          <div style={{display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, flexWrap: "wrap"}}>
            <label htmlFor="studio-movie-select" style={{fontSize: "0.85rem", color: "var(--muted)"}}>
              Which film?
            </label>
            <select
              id="studio-movie-select"
              value={movieId}
              onChange={(e) => {
                setMovieId(e.target.value);
                setLatestReview(null);
              }}
              style={{flex: 1, minWidth: 220}}
            >
              {movies.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.title}
                </option>
              ))}
            </select>
            {movieId && (
              <Link href={`/movies/${movieId}`} className="secondary button small">
                Open film
              </Link>
            )}
          </div>
        </div>
      )}

      {movieId && (
        <ReviewComposer
          movieId={movieId}
          onComplete={reload}
          onAnalyzed={(review) => {
            setLatestReview(review);
            reload();
          }}
        />
      )}

      {latestReview && (
        <section className="analysis-result" aria-live="polite">
          <div className="analysis-head">
            <div className={`sentiment ${latestReview.predictions.sentiment?.label ?? ""}`}>
              <div>
                <span>LIVE ANALYSIS STATUS</span>
                <strong>
                  {latestReview.predictions.sentiment?.label
                    ? latestReview.predictions.sentiment.label.toUpperCase()
                    : latestReview.analysis_status.replaceAll("_", " ")}
                </strong>
              </div>
            </div>
            <span className="tag lime">Revision {latestReview.revision}</span>
          </div>

          {latestReview.predictions.aspects?.aspects?.length ? (
            <div className="tags">
              {latestReview.predictions.aspects.aspects.map((a, idx) => (
                <span className="tag" key={idx}>
                  {a.aspect.replaceAll("_", " ")} · {a.label}
                </span>
              ))}
            </div>
          ) : null}

          {latestReview.predictions.themes?.theme_labels?.length ? (
            <div className="tags">
              {latestReview.predictions.themes.theme_labels.map((t) => (
                <span className="tag theme" key={t}>
                  {t.replaceAll("_", " ")}
                </span>
              ))}
            </div>
          ) : null}

          {latestReview.predictions.risk && (
            <div className="trust-box">
              <div>
                <strong>Review screening</strong>
                <div style={{color: "var(--muted)", fontSize: "0.78rem"}}>
                  {latestReview.predictions.risk.risk_index !== null &&
                  latestReview.predictions.risk.risk_index !== undefined
                    ? `Risk index: ${Math.round(latestReview.predictions.risk.risk_index)}`
                    : "No duplicate or promotional pattern detected."}
                </div>
              </div>
            </div>
          )}

          {!latestReview.predictions.sentiment?.label && auth.user && (
            <p className="muted" style={{fontSize: "0.82rem", marginTop: 10}}>
              Review saved ({latestReview.analysis_status}). Sentiment/aspect models await approval in the backend registry.
            </p>
          )}
        </section>
      )}

      <div className="section-heading">
        <div>
          <h2>The bigger picture</h2>
          <p>What collected reviews say about this film.</p>
        </div>
      </div>

      {error ? (
        <ErrorState message={error} retry={reload} />
      ) : !detail ? (
        <Loading />
      ) : (
        <div className="detail-columns">
          <div>
            <ReviewSummary summary={detail.summary} />
            <ReviewList reviews={reviews} />
          </div>
          <aside>
            <div className="panel">
              <AudienceScore score={detail.scores.overall} />
            </div>
            <ScoreProfile scores={detail.scores} />
          </aside>
        </div>
      )}
    </>
  );
}

