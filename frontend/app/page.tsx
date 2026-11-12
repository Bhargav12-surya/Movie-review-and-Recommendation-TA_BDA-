"use client";
import {useEffect, useState} from "react";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {api, posterURL} from "@/lib/api";
import type {Catalogue} from "@/lib/types";
import {MovieGrid} from "@/components/movie/card";
import {Loading, Empty, ErrorState} from "@/components/ui/states";
import {ArrowIcon, SearchIcon, SparkIcon} from "@/components/ui/icons";

const GENRES = ["Sci-Fi", "Romance", "Thriller", "Drama", "Adventure", "Comedy"];
const THEMES = ["Space", "Love", "Memory", "Artificial intelligence", "Family", "Identity", "Survival"];

export default function Home() {
  const [data, setData] = useState<Catalogue | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedGenre, setSelectedGenre] = useState("");
  const [selectedTheme, setSelectedTheme] = useState("");
  const [retry, setRetry] = useState(0);
  const router = useRouter();

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    const params = new URLSearchParams({page_size: "25"});
    if (selectedGenre) params.set("genre", selectedGenre);
    if (selectedTheme) params.set("theme", selectedTheme);
    api<Catalogue>(`/movies?${params.toString()}`, {signal: controller.signal})
      .then(setData)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [selectedGenre, selectedTheme, retry]);

  const featured =
    data?.movies.find((m) => m.backdrop_url) ??
    data?.movies.find((m) => m.poster_url) ??
    data?.movies[0];
  const spotlightImage = featured ? posterURL(featured.backdrop_url ?? featured.poster_url) : undefined;

  return (
    <>
      <div className="page-heading">
        <span className="eyebrow">THE GOOD PART STARTS HERE</span>
        <h1>Your next great watch.</h1>
        <p>Follow your taste. Find something unexpected.</p>
      </div>

      <form
        className="search-form"
        onSubmit={(event) => {
          event.preventDefault();
          const params = new URLSearchParams();
          if (query.trim()) params.set("q", query.trim());
          if (selectedGenre) params.set("genre", selectedGenre);
          if (selectedTheme) params.set("theme", selectedTheme);
          const qs = params.toString();
          router.push(qs ? `/discover?${qs}` : "/discover");
        }}
      >
        <SearchIcon size={18} />
        <label htmlFor="home-search" className="sr-only">
          Search the catalogue
        </label>
        <input
          id="home-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="A title, a genre, a feeling…"
          maxLength={200}
        />
        <button type="submit" className="search-submit" aria-label="Search movies">
          <ArrowIcon size={16} />
        </button>
      </form>

      <div className="filters" aria-label="Browse genres and themes">
        <button
          type="button"
          className={`filter ${!selectedGenre ? "selected" : ""}`}
          onClick={() => setSelectedGenre("")}
        >
          For you
        </button>
        {GENRES.map((genre) => (
          <button
            type="button"
            key={genre}
            className={`filter ${selectedGenre === genre ? "selected" : ""}`}
            onClick={() => setSelectedGenre(selectedGenre === genre ? "" : genre)}
          >
            {genre}
          </button>
        ))}

        <label className="theme-label">
          <span className="sr-only">Theme</span>
          <select
            aria-label="Filter by theme"
            value={selectedTheme}
            onChange={(event) => setSelectedTheme(event.target.value)}
          >
            <option value="">Any theme</option>
            {THEMES.map((theme) => (
              <option key={theme} value={theme}>
                {theme}
              </option>
            ))}
          </select>
        </label>
      </div>

      {featured && (
        <section
          className="spotlight"
          aria-label="In the spotlight"
          style={
            spotlightImage
              ? {
                  backgroundImage: `linear-gradient(90deg, rgba(9,14,17,.94) 4%, rgba(9,14,17,.58) 54%, rgba(9,14,17,.12)), url('${spotlightImage}')`,
                }
              : undefined
          }
        >
          <div className="spotlight-content">
            <span className="spotlight-label">
              <SparkIcon size={14} /> IN THE SPOTLIGHT
            </span>
            <h2>{featured.title}</h2>
            <div className="spotlight-meta">
              {featured.release_date?.slice(0, 4) ?? "—"}
              <span>·</span>
              {featured.runtime_minutes ? `${featured.runtime_minutes} min` : "—"}
              <span>·</span>
              {featured.genres.slice(0, 2).join(" / ") || "Local catalogue"}
            </div>
            <p>{featured.overview || "Explore audience sentiment and viewer reviews for this film."}</p>
            <div className="spotlight-actions">
              <Link href={`/movies/${featured.id}`} className="primary">
                Explore this film <ArrowIcon size={15} />
              </Link>
              <Link href={`/movies/${featured.id}#read-the-room`} className="ghost">
                Read the room
              </Link>
            </div>
          </div>
          <div className="spotlight-index">
            01 <span>/</span> YOUR CINEMA
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-heading">
          <div>
            <h2>{selectedGenre ? `${selectedGenre} films` : "Start your next obsession"}</h2>
            <p>
              {selectedGenre
                ? `Filtered by ${selectedGenre}${selectedTheme ? ` · ${selectedTheme}` : ""}.`
                : "A few possibilities. Rate a film to make this yours."}
            </p>
          </div>
          {data && <span className="result-count">{data.total.toLocaleString()} films</span>}
        </div>

        {error ? (
          <ErrorState message={error} retry={() => setRetry((value) => value + 1)} />
        ) : !data ? (
          <Loading />
        ) : !data.movies.length ? (
          <Empty
            title="No unseen films match every filter."
            description="Try another combination, or clear the genres and theme."
          />
        ) : (
          <MovieGrid movies={data.movies} />
        )}
      </section>
    </>
  );
}
