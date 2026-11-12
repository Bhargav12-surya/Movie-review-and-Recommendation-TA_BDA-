"use client";
import {useState} from "react";
import {useRouter} from "next/navigation";
import {api} from "@/lib/api";
import {useAuth} from "@/lib/auth";
import type {User} from "@/lib/types";

export default function Authentication() {
  const auth = useAuth();
  const router = useRouter();
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await api<{access_token: string; user: User}>(
        register ? "/auth/register" : "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({email, password, ...(register ? {display_name: name} : {})}),
        },
      );
      auth.signIn(result.access_token, result.user);
      setPassword("");
      router.push("/profile");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-box">
      <span className="eyebrow">YOUR CINEMA</span>
      <h1>{register ? "Create account." : "Welcome back."}</h1>
      <p className="muted">Save ratings, publish reviews, and chat with your companion.</p>

      <form className="form" onSubmit={submit}>
        {register && (
          <label>
            Display name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              maxLength={80}
              autoComplete="nickname"
            />
          </label>
        )}
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            maxLength={254}
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={12}
            maxLength={128}
            autoComplete={register ? "new-password" : "current-password"}
          />
        </label>
        <small style={{fontSize: "0.76rem"}}>Use 12–128 characters.</small>
        {error && (
          <p role="alert" className="notice error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          {busy ? "One moment…" : register ? "Create account" : "Sign in"}
        </button>
      </form>

      <p style={{marginTop: 18}}>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            setRegister((value) => !value);
            setError("");
          }}
        >
          {register ? "Already a member? Sign in" : "New here? Create an account"}
        </button>
      </p>
    </section>
  );
}
