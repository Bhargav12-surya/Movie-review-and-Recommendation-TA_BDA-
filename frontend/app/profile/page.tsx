"use client";
import {useEffect, useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import {Loading, Empty, ErrorState} from "@/components/ui/states";

type OwnReview = {
  id: string;
  movie_id: string;
  revision: number;
  text: string;
  language_code: string;
  training_permitted: boolean;
  evidence_permitted: boolean;
  moderation_permitted: boolean;
  consent_version: string;
  analysis_status: string;
};

type Profile = {
  preferences: {
    genres: Record<string, number>;
    themes: Record<string, number>;
    personalization_permitted: boolean;
  };
  ratings: Record<string, number>;
};

export default function ProfilePage() {
  const auth = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [genres, setGenres] = useState("");
  const [themes, setThemes] = useState("");
  const [consent, setConsent] = useState(false);
  const [reviews, setReviews] = useState<OwnReview[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [retry, setRetry] = useState(0);
  const [editId, setEditId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [draftEvidence, setDraftEvidence] = useState(false);
  const [draftTraining, setDraftTraining] = useState(false);
  const [draftModeration, setDraftModeration] = useState(false);

  useEffect(() => {
    if (!auth.token) return;
    const controller = new AbortController();
    setError("");
    api<Profile>("/me", {signal: controller.signal}, auth.token)
      .then((value) => {
        setProfile(value);
        setGenres(Object.keys(value.preferences.genres).join(", "));
        setThemes(Object.keys(value.preferences.themes).join(", "));
        setConsent(value.preferences.personalization_permitted);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    api<{reviews: OwnReview[]}>("/me/reviews", {signal: controller.signal}, auth.token)
      .then((value) => setReviews(value.reviews))
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [auth.token, retry]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const weights = (value: string) =>
        Object.fromEntries(
          value
            .split(",")
            .map((name) => name.trim())
            .filter(Boolean)
            .map((name) => [name, 1]),
        );
      await api(
        "/me/preferences",
        {
          method: "PUT",
          body: JSON.stringify({
            genres: weights(genres),
            themes: weights(themes),
            personalization_permitted: consent,
          }),
        },
        auth.token,
      );
      setNotice("Preferences saved.");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove(id: string) {
    try {
      await api(`/reviews/${id}`, {method: "DELETE"}, auth.token);
      setReviews((value) => value.filter((row) => row.id !== id));
      setNotice("Review deleted.");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function edit(row: OwnReview) {
    try {
      await api(
        `/reviews/${row.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            text: draft,
            language_code: row.language_code,
            training_permitted: draftTraining,
            evidence_permitted: draftEvidence,
            moderation_permitted: draftModeration,
            consent_version: row.consent_version,
            expected_revision: row.revision,
          }),
        },
        auth.token,
      );
      setEditId(null);
      setRetry((value) => value + 1);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!auth.user) {
    return (
      <Empty
        title="Your own corner of cinema."
        description="Sign in to manage your preferences, ratings and reviews."
        href="/auth"
        label="Sign in"
      />
    );
  }

  const ratingValues = profile ? Object.values(profile.ratings) : [];
  const averageRating = ratingValues.length
    ? (ratingValues.reduce((sum, val) => sum + val, 0) / ratingValues.length).toFixed(1)
    : "—";
  const genreTags = genres
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <>
      <header className="page-heading">
        <span className="eyebrow">A TASTE THAT’S ALL YOURS</span>
        <h1>{auth.user.display_name}</h1>
        <p>Your ratings, preferences, and reviews.</p>
      </header>

      <nav className="taste-tabs" aria-label="My taste sections">
        <Link href="/recommendations">For you</Link>
        <Link href="/watchlist">Watchlist</Link>
        <Link href="/profile" className="active">
          Preferences &amp; reviews
        </Link>
      </nav>

      {error && <ErrorState message={error} retry={() => setRetry((value) => value + 1)} />}

      {!profile ? (
        <Loading />
      ) : (
        <>
          <div className="taste-overview">
            <div className="taste-stat">
              <strong>{ratingValues.length}</strong>
              <span>films rated</span>
            </div>
            <div className="taste-stat">
              <strong>{averageRating}</strong>
              <span>average / 5</span>
            </div>
            <div className="taste-traits">
              <span>YOU’RE DRAWN TO</span>
              <div className="tags">
                {genreTags.length ? (
                  genreTags.map((tag) => (
                    <span className="tag lime" key={tag}>
                      {tag}
                    </span>
                  ))
                ) : (
                  <p>Add favourite genres below.</p>
                )}
              </div>
            </div>
          </div>

          <section className="panel">
            <h2>Your preferences</h2>
            <form className="form" onSubmit={save}>
              <label>
                Favourite genres, separated by commas
                <input
                  value={genres}
                  onChange={(event) => setGenres(event.target.value)}
                  maxLength={600}
                  placeholder="Drama, Sci-Fi, Romance"
                />
              </label>
              <label>
                Favourite theme identifiers, separated by commas
                <input
                  value={themes}
                  onChange={(event) => setThemes(event.target.value)}
                  maxLength={600}
                  placeholder="time_and_memory, love_and_family"
                />
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                />
                Allow ratings and selected preferences to personalize discovery.
              </label>
              <div>
                <button className="primary">Save preferences</button>
              </div>
            </form>
            {notice && (
              <p role="status" className="notice">
                {notice}
              </p>
            )}
          </section>

          <section className="section" style={{paddingTop: 4}}>
            <div className="section-heading" style={{marginTop: 8}}>
              <h2>Your reviews</h2>
              <span className="result-count">{reviews.length}</span>
            </div>
            {reviews.length ? (
              reviews.map((row) => (
                <article className="review" key={row.id}>
                  <div className="review-meta">
                    <span>Revision {row.revision}</span>
                    <span className="tag">{row.analysis_status.replaceAll("_", " ")}</span>
                  </div>
                  {editId === row.id ? (
                    <div className="form">
                      <textarea
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        minLength={10}
                        maxLength={20000}
                      />
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={draftEvidence}
                          onChange={(event) => setDraftEvidence(event.target.checked)}
                        />
                        Include in audience consensus
                      </label>
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={draftModeration}
                          onChange={(event) => setDraftModeration(event.target.checked)}
                        />
                        Run review screening
                      </label>
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={draftTraining}
                          onChange={(event) => setDraftTraining(event.target.checked)}
                        />
                        Allow research training
                      </label>
                      <div className="actions">
                        <button type="button" className="button small" onClick={() => edit(row)}>
                          Save revision
                        </button>
                        <button type="button" className="text-button" onClick={() => setEditId(null)}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p>{row.text}</p>
                  )}
                  <div className="actions">
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => {
                        setEditId(row.id);
                        setDraft(row.text);
                        setDraftEvidence(row.evidence_permitted);
                        setDraftTraining(row.training_permitted);
                        setDraftModeration(row.moderation_permitted);
                      }}
                    >
                      Edit
                    </button>
                    <button type="button" className="text-button" onClick={() => remove(row.id)}>
                      Delete review
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="empty-inline">No published reviews yet.</p>
            )}
          </section>
        </>
      )}
    </>
  );
}
