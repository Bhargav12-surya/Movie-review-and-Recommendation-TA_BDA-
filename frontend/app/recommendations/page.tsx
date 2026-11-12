"use client";
import {useEffect, useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {Recommendations} from "@/lib/types";
import {RecommendationShelf} from "@/components/recommendation/shelf";
import {Loading, Empty, ErrorState} from "@/components/ui/states";

export default function ForYou() {
  const auth = useAuth();
  const [data, setData] = useState<Recommendations | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!auth.token) return;
    const controller = new AbortController();
    setData(null);
    setError("");
    api<Recommendations>("/recommendations", {signal: controller.signal}, auth.token)
      .then(setData)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [auth.token, retry]);

  return (
    <>
      <header className="page-heading">
        <span className="eyebrow">A TASTE THAT’S ALL YOURS</span>
        <h1>Your cinematic fingerprint.</h1>
        <p>Your ratings and preferences shape every next pick.</p>
      </header>

      <nav className="taste-tabs" aria-label="My taste sections">
        <Link href="/recommendations" className="active">
          For you
        </Link>
        <Link href="/watchlist">Watchlist</Link>
        <Link href="/profile">Preferences &amp; reviews</Link>
      </nav>

      {!auth.user ? (
        <Empty
          title="The first film is up to you."
          description="Sign in to view personalized recommendations and ratings."
          href="/auth"
          label="Sign in"
        />
      ) : error ? (
        <ErrorState message={error} retry={() => setRetry((value) => value + 1)} />
      ) : !data ? (
        <Loading />
      ) : !data.recommendations.length ? (
        <Empty
          title={
            data.status === "preferences_required"
              ? "Add a little direction."
              : "Your shelf is waiting."
          }
          description={data.message ?? "Add genre or theme preferences to start."}
          href="/profile"
          label="Edit preferences"
        />
      ) : (
        <>
          <div className="section-heading" style={{marginTop: 8}}>
            <div>
              <h2>Picked for your taste</h2>
              <p>{data.cold_start ? "Preference-based discovery" : "Hybrid discovery"}</p>
            </div>
            <span className="result-count">{data.recommendations.length} films</span>
          </div>
          <RecommendationShelf items={data.recommendations} />
        </>
      )}
    </>
  );
}
