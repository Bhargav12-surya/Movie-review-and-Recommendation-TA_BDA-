"use client";
import {useEffect, useRef, useState} from "react";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {ChatReply} from "@/lib/types";
import {MovieGrid} from "@/components/movie/card";
import {VoiceInput} from "@/components/chat/voice";
import {AudienceScore} from "@/components/score/profile";
import {ReviewSummary} from "@/components/review/summary";
import {Empty, Loading} from "@/components/ui/states";
import {ArrowIcon, SparkIcon} from "@/components/ui/icons";

type Turn = {query: string; reply?: ChatReply};

const SUGGESTIONS = [
  "Recommend romance and science-fiction movies",
  "Show movies similar to Interstellar",
  "Compare Arrival and Interstellar",
];

export default function Assistant() {
  const auth = useAuth();
  const [text, setText] = useState("");
  const [conversation, setConversation] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const log = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!pending || !auth.token) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const result = await api<{status: string; reply: ChatReply}>(
          `/chat/turns/${pending}`,
          {signal: controller.signal},
          auth.token,
        );
        if (result.status === "complete" || result.status === "failed") {
          setTurns((rows) =>
            rows.map((row, index) => (index === rows.length - 1 ? {...row, reply: result.reply} : row)),
          );
          setPending(null);
          return;
        }
        timer = setTimeout(poll, 1200);
      } catch (err) {
        if (!controller.signal.aborted) {
          setError((err as Error).message);
          setPending(null);
        }
      }
    }

    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [pending, auth.token]);

  useEffect(() => {
    log.current?.scrollIntoView({behavior: "smooth", block: "end"});
  }, [turns, pending]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim() || pending) return;
    setError("");
    const query = text;
    try {
      const result = await api<{turn_id: string; conversation_id: string}>(
        "/chat/query",
        {method: "POST", body: JSON.stringify({text: query, conversation_id: conversation})},
        auth.token,
      );
      setConversation(result.conversation_id);
      setTurns((rows) => [...rows, {query}]);
      setText("");
      setPending(result.turn_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function clear() {
    try {
      if (conversation) {
        await api(`/chat/conversations/${conversation}`, {method: "DELETE"}, auth.token);
      }
      setConversation(null);
      setTurns([]);
      setPending(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="chat-shell">
      <header className="page-heading">
        <span className="eyebrow">LET’S FIND YOUR NEXT FILM</span>
        <h1>What are you in the mood for?</h1>
        <p>A genre, a feeling, or a film title. Start anywhere.</p>
      </header>

      {!auth.user ? (
        <Empty
          title="Let’s find your next film."
          description="Sign in to start a conversation with Ask Framewise."
          href="/auth"
          label="Sign in"
        />
      ) : (
        <section className="chat-panel">
          {!turns.length && (
            <div className="prompt-list" style={{marginTop: 0, marginBottom: 18}}>
              {SUGGESTIONS.map((example) => (
                <button type="button" key={example} onClick={() => setText(example)}>
                  <span>{example}</span>
                  <ArrowIcon size={14} />
                </button>
              ))}
            </div>
          )}

          <div className="chat-log" aria-live="polite">
            {turns.map((turn, index) => (
              <div key={index} style={{display: "grid", gap: 12}}>
                <article className="chat-message user">
                  <p>{turn.query}</p>
                </article>
                {turn.reply && (
                  <article className="chat-message">
                    <span className="eyebrow" style={{display: "flex", alignItems: "center", gap: 6}}>
                      <SparkIcon size={13} style={{color: "var(--lime)"}} />
                      {turn.reply.status.replaceAll("_", " ")}
                    </span>
                    <p>{turn.reply.text}</p>
                    {turn.reply.movies?.length ? <MovieGrid movies={turn.reply.movies} /> : null}
                    {turn.reply.movies
                      ?.filter((movie) => movie.scores)
                      .map((movie) => (
                        <section className="panel" key={movie.id} style={{marginTop: 14, marginBottom: 0}}>
                          <h3>{movie.title}</h3>
                          <AudienceScore score={movie.scores.overall} />
                          {movie.summary && <ReviewSummary summary={movie.summary} />}
                        </section>
                      ))}
                    {turn.reply.evidence?.length ? (
                      <div className="evidence-list">
                        {turn.reply.evidence.map((item, idx) => (
                          <blockquote key={item.review_id + idx}>
                            <p>“{item.quote}”</p>
                            <cite>
                              Review {item.review_id.slice(0, 8)} · {item.label}
                            </cite>
                          </blockquote>
                        ))}
                      </div>
                    ) : null}
                  </article>
                )}
              </div>
            ))}
            {pending && <Loading label="Searching catalogue…" />}
            <div ref={log} />
          </div>

          {error && (
            <p role="alert" className="notice error" style={{marginBottom: 12}}>
              {error}
            </p>
          )}

          <form className="chat-form" onSubmit={send}>
            <textarea
              aria-label="Movie discovery query"
              value={text}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              maxLength={2000}
              required
              placeholder="Tell me what you’re in the mood for…"
            />
            <VoiceInput onText={setText} />
            <button className="primary" disabled={!!pending}>
              Discover →
            </button>
          </form>

          <div className="assistant-foot" style={{marginTop: 12}}>
            <span>Catalog-based discovery</span>
            <button type="button" className="text-button" onClick={clear}>
              Clear conversation
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
