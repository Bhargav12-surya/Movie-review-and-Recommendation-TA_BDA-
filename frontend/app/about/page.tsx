export default function About() {
  return (
    <article className="prose">
      <header className="page-heading">
        <span className="eyebrow">BEHIND THE SCREEN</span>
        <h1>Movie Review &amp; Recommendation System</h1>
        <p>A combined Big Data Analysis and Text Analytics project.</p>
      </header>

      <div className="info-box">
        <strong>Local Python API &amp; PostgreSQL connected</strong>
        <p>
          Catalogue search, reviews, ratings, watchlists, and grounded companion queries run against the local FastAPI backend and PostgreSQL database.
        </p>
        <p>
          Audience sentiment scores appear only when approved models and sufficient evidence exist. Star ratings and personalized matches stay distinct.
        </p>
      </div>

      <div className="credits">
        <img src="/assets/tmdb-attribution-logo.svg" alt="TMDB" width={85} />
        <p>This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
        <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer">
          Movie images: TMDB
        </a>
      </div>
    </article>
  );
}
