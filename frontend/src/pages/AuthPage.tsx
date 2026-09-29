import { FormEvent, useState } from "react";

import { api } from "../services/api";

interface AuthPageProps {
  onLogin: (email: string, password: string) => Promise<void>;
}

export function AuthPage({ onLogin }: AuthPageProps) {
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (registering) {
        await api.register(email, password);
      }
      await onLogin(email, password);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-layout">
      <section className="auth-card">
        <p className="eyebrow">DocNexus AI</p>
        <h1>{registering ? "Create your account" : "Welcome back"}</h1>
        <p className="muted">A secure workspace for your PDF documents.</p>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
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
              minLength={registering ? 8 : 1}
              autoComplete={registering ? "new-password" : "current-password"}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button disabled={busy}>{busy ? "Please wait…" : registering ? "Register" : "Login"}</button>
        </form>
        <button className="text-button" onClick={() => setRegistering(!registering)}>
          {registering ? "Already registered? Login" : "Need an account? Register"}
        </button>
      </section>
    </main>
  );
}
