"use client";
import {useEffect, useRef, useState} from "react";
import Link from "next/link";
import {usePathname, useRouter} from "next/navigation";
import {api, posterURL} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {ChatReply, MovieDetail} from "@/lib/types";
import {
  ArrowIcon,
  ChatIcon,
  CloseIcon,
  DiscoverIcon,
  HeartIcon,
  InfoIcon,
  MicIcon,
  ReviewIcon,
  SendIcon,
  SparkIcon,
} from "@/components/ui/icons";

type QuickTurn = {
  query: string;
  reply?: ChatReply;
  error?: string;
};

function breadcrumbFor(pathname: string): string {
  if (pathname === "/" || pathname.startsWith("/discover")) return "Discover";
  if (pathname.startsWith("/studio")) return "Review studio";
  if (
    pathname.startsWith("/recommendations") ||
    pathname.startsWith("/watchlist") ||
    pathname.startsWith("/profile")
  ) {
    return "My taste";
  }
  if (pathname.startsWith("/assistant")) return "Ask Framewise";
  if (pathname.startsWith("/movies/")) return "Film detail";
  if (pathname.startsWith("/about")) return "About";
  if (pathname.startsWith("/auth")) return "Account";
  return "Discover";
}

function QuickPoster({movie}: {movie: MovieDetail}) {
  const [failed, setFailed] = useState(false);
  const url = posterURL(movie.poster_url);
  if (url && !failed) {
    return <img src={url} alt={movie.title} loading="lazy" onError={() => setFailed(true)} />;
  }
  return (
    <div className="poster-placeholder">
      <SparkIcon size={16} />
    </div>
  );
}

export function Shell({children}: {children: React.ReactNode}) {
  const auth = useAuth();
  const router = useRouter();
  const path = usePathname() ?? "/";
  const isAssistantPage = path.startsWith("/assistant");

  const [mobileChatOpen, setMobileChatOpen] = useState(false);
  const [quickInput, setQuickInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<QuickTurn[]>([]);
  const [pendingTurnId, setPendingTurnId] = useState<string | null>(null);
  const [quickError, setQuickError] = useState("");
  const logEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMobileChatOpen(false);
  }, [path]);

  useEffect(() => {
    if (!pendingTurnId || !auth.token) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const result = await api<{status: string; reply: ChatReply}>(
          `/chat/turns/${pendingTurnId}`,
          {signal: controller.signal},
          auth.token,
        );
        if (result.status === "complete" || result.status === "failed") {
          setTurns((rows) =>
            rows.map((row, idx) => (idx === rows.length - 1 ? {...row, reply: result.reply} : row)),
          );
          setPendingTurnId(null);
          return;
        }
        timer = setTimeout(poll, 1200);
      } catch (error) {
        if (!controller.signal.aborted) {
          setQuickError((error as Error).message);
          setPendingTurnId(null);
        }
      }
    }

    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [pendingTurnId, auth.token]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({behavior: "smooth", block: "end"});
  }, [turns, pendingTurnId]);

  async function logout() {
    try {
      await api("/auth/logout", {method: "POST"}, auth.token);
    } finally {
      auth.clear();
      setConversationId(null);
      setTurns([]);
      setPendingTurnId(null);
      router.push("/");
    }
  }

  async function sendQuickChat(overrideText?: string) {
    const query = (overrideText ?? quickInput).trim();
    if (!query || pendingTurnId) return;
    setQuickError("");

    if (!auth.token) {
      setTurns((rows) => [
        ...rows,
        {
          query,
          error: "Sign in to chat with your movie companion.",
        },
      ]);
      if (!overrideText) setQuickInput("");
      return;
    }

    try {
      const result = await api<{turn_id: string; conversation_id: string}>(
        "/chat/query",
        {method: "POST", body: JSON.stringify({text: query, conversation_id: conversationId})},
        auth.token,
      );
      setConversationId(result.conversation_id);
      setTurns((rows) => [...rows, {query}]);
      if (!overrideText) setQuickInput("");
      setPendingTurnId(result.turn_id);
    } catch (error) {
      setQuickError((error as Error).message);
    }
  }

  async function resetQuickChat() {
    try {
      if (conversationId && auth.token) {
        await api(`/chat/conversations/${conversationId}`, {method: "DELETE"}, auth.token);
      }
    } catch {
      // Ignore already-expired conversation
    } finally {
      setConversationId(null);
      setTurns([]);
      setPendingTurnId(null);
      setQuickError("");
    }
  }

  const initialLetter = auth.user?.display_name?.trim().charAt(0).toUpperCase() || "Y";
  const isDiscoverActive = path === "/" || path.startsWith("/discover");
  const isTasteActive =
    path.startsWith("/recommendations") ||
    path.startsWith("/watchlist") ||
    path.startsWith("/profile");

  return (
    <div className="app-shell">
      <a className="skip" href="#content">
        Skip to content
      </a>

      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Framewise home">
          <img src="/favicon.svg" alt="" width={34} height={34} />
          <span>
            frame<span className="brand-thin">wise</span>
            <small>MOVIE INTELLIGENCE</small>
          </span>
        </Link>

        <p className="nav-label">YOUR CINEMA</p>
        <nav aria-label="Main navigation">
          <Link href="/discover" aria-current={isDiscoverActive ? "page" : undefined}>
            <DiscoverIcon size={18} />
            Discover
          </Link>
          <Link href="/studio" aria-current={path.startsWith("/studio") ? "page" : undefined}>
            <ReviewIcon size={18} />
            Review studio
          </Link>
          <Link href="/recommendations" aria-current={isTasteActive ? "page" : undefined}>
            <HeartIcon size={18} />
            My taste
          </Link>
          <Link
            href="/assistant"
            aria-label="Film companion"
            aria-current={path.startsWith("/assistant") ? "page" : undefined}
          >
            <ChatIcon size={18} />
            <span>Ask Framewise</span>
            <span className="mini-label" aria-hidden="true">
              AI
            </span>
          </Link>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-note">
            A film for every
            <br />
            <em>version of you.</em>
          </div>

          <Link href="/about" className="about-button">
            <InfoIcon size={16} />
            About this project
          </Link>

          <div className="profile">
            {auth.user ? (
              <>
                <Link href="/profile" className="profile-link">
                  <div className="avatar" aria-hidden="true">
                    {initialLetter}
                  </div>
                  <div>
                    <strong>{auth.user.display_name}</strong>
                    <small>Personal movie space</small>
                  </div>
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  className="text-button"
                  aria-label="Sign out"
                >
                  Out
                </button>
              </>
            ) : (
              <Link href="/auth" className="profile-link">
                <div className="avatar" aria-hidden="true">
                  Y
                </div>
                <div>
                  <strong>You</strong>
                  <small>Sign in</small>
                </div>
              </Link>
            )}
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <span className="topbar-breadcrumb">
            Your cinema <span>/</span> {breadcrumbFor(path)}
          </span>

          <div className="topbar-actions">
            {!isAssistantPage && (
              <button
                type="button"
                className="mode-pill mobile-chat-toggle"
                onClick={() => setMobileChatOpen(true)}
              >
                <SparkIcon size={14} />
                Ask AI
              </button>
            )}

            <Link href="/about" className="mode-pill">
              Local catalog
              <InfoIcon size={14} />
            </Link>

            <div className="topbar-mobile-auth">
              {auth.user ? (
                <>
                  <Link href="/profile">{auth.user.display_name}</Link>
                  <button type="button" onClick={logout} className="text-button">
                    Sign out
                  </button>
                </>
              ) : (
                <Link href="/auth" className="button small secondary">
                  Sign in
                </Link>
              )}
            </div>
          </div>
        </header>

        <div className={isAssistantPage ? "workspace-grid single-col" : "workspace-grid"}>
          <main id="content" tabIndex={-1}>
            {children}
          </main>

          {!isAssistantPage && (
            <aside
              className={`assistant ${mobileChatOpen ? "mobile-open" : ""}`}
              aria-label="Ask Framewise"
            >
              <div className="assistant-head">
                <div className="cine-avatar">
                  <SparkIcon size={18} />
                </div>
                <div>
                  <h2>Ask Framewise</h2>
                  <span>Your movie companion</span>
                </div>
                <button
                  type="button"
                  className="icon-button assistant-close"
                  aria-label="Close companion"
                  onClick={() => setMobileChatOpen(false)}
                >
                  <CloseIcon size={18} />
                </button>
              </div>

              <div className="conversation" role="log" aria-live="polite">
                {!turns.length ? (
                  <>
                    <div className="cine-greeting">
                      <span className="mini-label">LET’S FIND YOUR NEXT FILM</span>
                      <h3>
                        What are you
                        <br />
                        in the mood for?
                      </h3>
                      <p>A genre, a feeling, or something hard to describe. Start anywhere.</p>
                    </div>
                    <div className="prompt-list">
                      {[
                        "Sci-fi with a little romance",
                        "How is Interstellar?",
                        "Drama movies under 120 minutes",
                      ].map((prompt) => (
                        <button
                          key={prompt}
                          type="button"
                          onClick={() => void sendQuickChat(prompt)}
                        >
                          <span>{prompt}</span>
                          <ArrowIcon size={14} />
                        </button>
                      ))}
                    </div>
                  </>
                ) : (
                  <>
                    {turns.map((turn, idx) => (
                      <div key={idx}>
                        <div className="message user">{turn.query}</div>
                        {turn.error ? (
                          <div className="message cine">
                            <SparkIcon size={16} />
                            <p>{turn.error}</p>
                            {!auth.user && (
                              <div className="actions" style={{marginTop: 10}}>
                                <Link href="/auth" className="button small">
                                  Sign in
                                </Link>
                              </div>
                            )}
                          </div>
                        ) : turn.reply ? (
                          <div className="message cine">
                            <SparkIcon size={16} />
                            <p>{turn.reply.text}</p>
                            {turn.reply.movies?.length ? (
                              <div className="chat-movies">
                                {turn.reply.movies.slice(0, 4).map((m) => (
                                  <Link key={m.id} href={`/movies/${m.id}`}>
                                    <span className="chat-poster">
                                      <QuickPoster movie={m} />
                                    </span>
                                    <span>
                                      <strong>{m.title}</strong>
                                      <small>
                                        {m.release_date?.slice(0, 4) ?? "—"} ·{" "}
                                        {m.genres.slice(0, 2).join(" / ")}
                                      </small>
                                    </span>
                                    <ArrowIcon size={13} />
                                  </Link>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    ))}
                    {pendingTurnId && (
                      <div className="message cine">
                        <SparkIcon size={16} />
                        <p className="muted">Finding the right films…</p>
                      </div>
                    )}
                    {quickError && (
                      <div className="message cine">
                        <p className="notice error">{quickError}</p>
                      </div>
                    )}
                    <div ref={logEndRef} />
                  </>
                )}
              </div>

              <form
                className="chat-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void sendQuickChat();
                }}
              >
                <label htmlFor="quick-companion-input" className="sr-only">
                  Ask about movies
                </label>
                <textarea
                  id="quick-companion-input"
                  rows={2}
                  value={quickInput}
                  onChange={(e) => setQuickInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void sendQuickChat();
                    }
                  }}
                  placeholder="Tell me what you’re in the mood for…"
                  maxLength={2000}
                />
                <div className="chat-actions">
                  <Link
                    href="/assistant"
                    className="icon-button"
                    aria-label="Open voice input"
                    title="Voice & full companion"
                  >
                    <MicIcon size={15} />
                  </Link>
                  <span>Type or use your voice</span>
                  <button
                    className="send-button"
                    type="submit"
                    aria-label="Send message"
                    disabled={!!pendingTurnId}
                  >
                    <SendIcon size={15} />
                  </button>
                </div>
              </form>

              <div className="assistant-foot">
                <span>Catalog-based discovery</span>
                <button type="button" onClick={() => void resetQuickChat()}>
                  New chat
                </button>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
