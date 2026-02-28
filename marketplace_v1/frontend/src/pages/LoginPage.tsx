import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../app/auth";
import { ApiError } from "../api/client";
import { AppShell } from "../components/layout/AppShell";

export function LoginPage() {
  const { login, bootstrapAdmin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const bootstrap = async () => {
    setBusy(true);
    setError(null);
    try {
      await bootstrapAdmin(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bootstrap failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell>
      <h1>Login</h1>
      <form onSubmit={submit} style={{ display: "grid", gap: 10, maxWidth: 360 }}>
        <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={busy}>Sign In</button>
        <button type="button" onClick={bootstrap} disabled={busy}>
          Bootstrap First Admin
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </AppShell>
  );
}
