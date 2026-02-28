import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../app/auth";

export function DashboardPage() {
  const { user } = useAuth();

  return (
    <AppShell>
      <h1>Marketplace Dashboard</h1>
      {!user ? (
        <p>Sign in or register to place orders.</p>
      ) : (
        <>
          <p>Logged in as <strong>{user.email}</strong>.</p>
          <p>Roles: {user.roles.join(", ")}</p>
          <ul>
            <li>Buyers/Sellers: place and track orders.</li>
            <li>Admins: manage inventory and users.</li>
            <li>Super Admin: manage admin access.</li>
          </ul>
        </>
      )}
    </AppShell>
  );
}
