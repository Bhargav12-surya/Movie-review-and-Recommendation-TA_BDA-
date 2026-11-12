"use client";
import {useEffect, useState} from "react";
import {useSearchParams, useRouter} from "next/navigation";
import {api} from "@/lib/api";
import type {Catalogue} from "@/lib/types";
import {MovieGrid} from "./card";
import {Loading, Empty, ErrorState} from "@/components/ui/states";
import {ArrowIcon, SearchIcon} from "@/components/ui/icons";

const GENRES = ["Sci-Fi", "Romance", "Thriller", "Drama", "Adventure", "Comedy", "Action"];
const THEMES = ["Space", "Love", "Memory", "Artificial intelligence", "Family", "Identity", "Survival"];

export function Discover() {
  const params = useSearchParams();
  const router = useRouter();
  const query = params.get("q") ?? "";
  const genre = params.get("genre") ?? "";
  const theme = params.get("theme") ?? "";

  const [text, setText] = useState(query);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Catalogue | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setText(query);
    setPage(1);
  }, [query, genre, theme]);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    const search = new URLSearchParams({page: String(page), page_size: "25"});
    if (query) search.set("q", query);
    if (genre) search.set("genre", genre);
    if (theme) search.set("theme", theme);
    api<Catalogue>(`/movies?${search.toString()}`, {signal: controller.signal})
      .then(setData)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [query, genre, theme, page, retry]);

  function pushSearch(nextQ: string, nextGenre: string, nextTheme: string) {
    const search = new URLSearchParams();
    if (nextQ.trim()) search.set("q", nextQ.trim());
    if (nextGenre) search.set("genre", nextGenre);
    if (nextTheme) search.set("theme", nextTheme);
    const qs = search.toString();
    router.push(qs ? `/discover?${qs}` : "/discover");
  }

  return (
    <>
      <header className="page-heading">
        <span className="eyebrow">THE GOOD PART STARTS HERE</span>
        <h1>Your next great watch.</h1>
        <p>Follow your taste. Find something unexpected.</p>
      </header>

      <form
        className="search-form"
        onSubmit={(event) => {
          event.preventDefault();
          pushSearch(text, genre, theme);
        }}
      >
        <SearchIcon size={18} />
        <input
          aria-label="Search movie titles"
          placeholder="A title, a genre, a feeling…"
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={200}
        />
        <button type="submit" className="search-submit" aria-label="Find a film">
          <ArrowIcon size={16} />
        </button>
      </form>

      <div className="filters" aria-label="Filter by genre and theme">
        <button
          type="button"
          className={`filter ${!genre ? "selected" : ""}`}
          onClick={() => pushSearch(text, "", theme)}
        >
          For you
        </button>
        {GENRES.map((item) => (
          <button
            type="button"
            key={item}
            className={`filter ${genre === item ? "selected" : ""}`}
            onClick={() => pushSearch(text, genre === item ? "" : item, theme)}
          >
            {item}
          </button>
        ))}

        <label className="theme-label">
          <span className="sr-only">Theme</span>
          <select
            aria-label="Filter by theme"
            value={theme}
            onChange={(event) => pushSearch(text, genre, event.target.value)}
          >
            <option value="">Any theme</option>
            {THEMES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? (
        <ErrorState message={error} retry={() => setRetry((value) => value + 1)} />
      ) : !data ? (
        <Loading />
      ) : !data.movies.length ? (
        <Empty
          title="No films in this frame."
          description="Try another title, genre, or theme."
        />
      ) : (
        <section className="section">
          <div className="section-heading">
            <div>
              <h2>{query ? `Results for “${query}”` : "From the catalogue"}</h2>
              <p>{genre ? `Matching ${genre}` : "Rate or review any film to personalize your shelf."}</p>
            </div>
            <span className="result-count">{data.total.toLocaleString()} films</span>
          </div>

          <MovieGrid movies={data.movies} />

          <div className="pagination">
            <button
              type="button"
              className="secondary"
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
            >
              Previous
            </button>
            <span>Page {page}</span>
            <button
              type="button"
              className="secondary"
              disabled={page * data.page_size >= data.total}
              onClick={() => setPage((value) => value + 1)}
            >
              Next
            </button>
          </div>
        </section>
      )}
    </>
  );
}
