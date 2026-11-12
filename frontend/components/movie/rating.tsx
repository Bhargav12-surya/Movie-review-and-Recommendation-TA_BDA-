"use client";
import {useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";

export function RatingControl({
  movieId,
  onSaved,
}: {
  movieId: string;
  onSaved: () => void;
}) {
  const auth = useAuth();
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api(
        `/me/ratings/${movieId}`,
        {method: "PUT", body: JSON.stringify({value: Number(value)})},
        auth.token,
      );
      setMessage("Rating saved.");
      onSaved();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Your rating</h2>
      {auth.user ? (
        <form className="form" onSubmit={save}>
          <label>
            Stars
            <select required value={value} onChange={(event) => setValue(event.target.value)}>
              <option value="">Select rating</option>
              {Array.from({length: 10}, (_, index) => (index + 1) / 2).map((stars) => (
                <option value={stars} key={stars}>
                  {stars} / 5
                </option>
              ))}
            </select>
          </label>
          <button className="primary" disabled={!value || busy}>
            {busy ? "Saving…" : "Save rating"}
          </button>
        </form>
      ) : (
        <p className="muted" style={{fontSize: "0.86rem"}}>
          <Link href="/auth" style={{color: "var(--lime)", textDecoration: "underline"}}>
            Sign in
          </Link>{" "}
          to rate this film.
        </p>
      )}
      {auth.user && (
        <div style={{marginTop: 12}}>
          <button
            className="text-button"
            type="button"
            onClick={async () => {
              try {
                await api(
                  `/me/interactions/${movieId}`,
                  {method: "PUT", body: JSON.stringify({event_type: "watched"})},
                  auth.token,
                );
                setMessage("Marked as watched.");
              } catch (error) {
                setMessage((error as Error).message);
              }
            }}
          >
            Mark as watched
          </button>
        </div>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
    </section>
  );
}
