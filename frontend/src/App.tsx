import { AuthPage } from "./pages/AuthPage";
import { Dashboard } from "./pages/Dashboard";
import { useSession } from "./hooks/useSession";

export default function App() {
  const { user, loading, login, logout } = useSession();

  if (loading) {
    return <main className="loading">Loading DocNexus AI…</main>;
  }
  return user ? (
    <Dashboard user={user} onLogout={logout} />
  ) : (
    <AuthPage onLogin={login} />
  );
}
