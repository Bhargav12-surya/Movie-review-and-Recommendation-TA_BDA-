"use client";
import {useState, useEffect, useRef} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {Review} from "@/lib/types";
import {ArrowIcon, SparkIcon} from "@/components/ui/icons";

export function ReviewComposer({
  movieId,
  onComplete,
  onAnalyzed,
}: {
  movieId: string;
  onComplete: () => void;
  onAnalyzed?: (review: Review) => void;
}) {
  const auth = useAuth();
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("en");
  const [evidence, setEvidence] = useState(true);
  const [training, setTraining] = useState(false);
  const [moderation, setModeration] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [id, setId] = useState<string | null>(null);
  const key = useRef<string | null>(null);

  useEffect(() => {
    if (!id || !auth.token) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let count = 0;

    async function poll() {
      try {
        const review = await api<Review>(`/reviews/${id}`, {}, auth.token);
        if (cancelled) return;
        setNotice(`Review saved · ${review.analysis_status}`);
        if (
          ["complete", "partial", "unavailable", "failed", "unsupported"].includes(
            review.analysis_status,
          )
        ) {
          onAnalyzed?.(review);
          onComplete();
          return;
        }
        if (++count < 30) timer = setTimeout(poll, 1000);
        else setNotice("Review saved. Analysis is still queued.");
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, auth.token, onComplete, onAnalyzed]);

  if (!auth.user) {
    return (
      <section className="panel">
        <h2>Write a review</h2>
        <p className="muted" style={{marginBottom: 14, fontSize: "0.88rem"}}>
          Sign in to publish a review and run live sentiment and aspect analysis.
        </p>
        <Link href="/auth" className="primary">
          Sign in to review <ArrowIcon size={15} />
        </Link>
      </section>
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    key.current ??= crypto.randomUUID();
    try {
      const result = await api<{review_id: string}>(
        `/movies/${movieId}/reviews`,
        {
          method: "POST",
          headers: {"Idempotency-Key": key.current},
          body: JSON.stringify({
            text,
            language_code: language,
            evidence_permitted: evidence,
            training_permitted: training,
            moderation_permitted: moderation,
            consent_version: "review-consent-v1",
          }),
        },
        auth.token,
      );
      setId(result.review_id);
      setText("");
      key.current = null;
      setNotice("Queued for analysis…");
      onComplete();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  return (
    <form className="studio-editor" onSubmit={submit}>
      <div className="editor-header">
        <span style={{display: "inline-flex", alignItems: "center", gap: 8, color: "var(--muted)", fontSize: "0.85rem"}}>
          <SparkIcon size={15} style={{color: "var(--lime)"}} />
          Write your review
        </span>
        <label>
          Language
          <select
            value={language}
            onChange={(event) => {
              setLanguage(event.target.value);
              key.current = null;
            }}
          >
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="hi-Latn">Romanized Hindi</option>
            <option value="mul">Hinglish</option>
          </select>
        </label>
      </div>

      <label className="sr-only" htmlFor="review-composer-text">
        Your review
      </label>
      <textarea
        id="review-composer-text"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          key.current = null;
        }}
        required
        minLength={10}
        maxLength={20000}
        placeholder="The visuals were stunning and the acting felt natural. I loved the soundtrack, though the middle felt slow…"
      />

      <div className="editor-consent">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={evidence}
            onChange={(event) => {
              setEvidence(event.target.checked);
              key.current = null;
            }}
          />
          Include in audience consensus &amp; summaries
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={moderation}
            onChange={(event) => {
              setModeration(event.target.checked);
              key.current = null;
            }}
          />
          Run review screening checks
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={training}
            onChange={(event) => {
              setTraining(event.target.checked);
              key.current = null;
            }}
          />
          Allow for future research training
        </label>
        {error && (
          <p role="alert" className="notice error">
            {error}
          </p>
        )}
        {notice && (
          <p role="status" className="notice">
            {notice}
          </p>
        )}
      </div>

      <div className="editor-footer">
        <span className="word-count">
          {words} word{words === 1 ? "" : "s"}
        </span>
        <button className="primary" disabled={busy}>
          {busy ? "Saving…" : "Publish review"} <ArrowIcon size={15} />
        </button>
      </div>
    </form>
  );
}
