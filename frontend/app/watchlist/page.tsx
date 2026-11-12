"use client";
import {useEffect, useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {Movie} from "@/lib/types";
import {MovieCard} from "@/components/movie/card";
import {Loading, Empty, ErrorState} from "@/components/ui/states";

export default function Watchlist() {
  const auth = useAuth();
  const [movies, setMovies] = useState<Movie[] | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!auth.token) return;
    const controller = new AbortController();
    setError("");
    api<{movies: Movie[]}>("/me/watchlist", {signal: controller.signal}, auth.token)
      .then((value) => setMovies(value.movies))
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [auth.token, retry]);

  async function remove(id: string) {
    try {
      await api(`/me/watchlist/${id}`, {method: "DELETE"}, auth.token);
      setMovies((rows) => rows?.filter((row) => row.id !== id) ?? []);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <>
      <header className="page-heading">
        <span className="eyebrow">SAVED FOR LATER</span>
        <h1>Your watchlist.</h1>
        <p>Keep the films you want to return to.</p>
      </header>

      <nav className="taste-tabs" aria-label="My taste sections">
        <Link href="/recommendations">For you</Link>
        <Link href="/watchlist" className="active">
          Watchlist
        </Link>
        <Link href="/profile">Preferences &amp; reviews</Link>
      </nav>

      {!auth.user ? (
        <Empty
          title="A shelf of your own."
          description="Sign in to save and manage your watchlist."
          href="/auth"
          label="Sign in"
        />
      ) : error ? (
        <ErrorState message={error} retry={() => setRetry((value) => value + 1)} />
      ) : !movies ? (
        <Loading />
      ) : !movies.length ? (
        <Empty
          title="Nothing saved yet."
          description="Open any film and add it to your watchlist."
          href="/discover"
        />
      ) : (
        <section className="section" style={{paddingTop: 4}}>
          <div className="section-heading" style={{marginTop: 8}}>
            <h2>Saved titles</h2>
            <span className="result-count">{movies.length} films</span>
          </div>
          <div className="movie-grid">
            {movies.map((movie) => (
              <div key={movie.id}>
                <MovieCard movie={movie} />
                <button
                  type="button"
                  className="text-button"
                  style={{fontSize: "0.75rem", marginTop: 6}}
                  onClick={() => remove(movie.id)}
                >
                  Remove from watchlist
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
