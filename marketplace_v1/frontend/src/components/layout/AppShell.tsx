import type { ReactNode } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import { useAuth } from "../../app/auth";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 20 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <nav style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <RouterLink to="/">Dashboard</RouterLink>
          {!user && <RouterLink to="/login">Login</RouterLink>}
          {!user && <RouterLink to="/register">Register</RouterLink>}
          {user && <RouterLink to="/orders">Orders</RouterLink>}
          {user && <RouterLink to="/profile">My Profile</RouterLink>}
          {user && (hasRole("admin") || hasRole("super_admin") || hasRole("seller")) && (
            <RouterLink to="/inventory">Inventory</RouterLink>
          )}
          {user && (hasRole("admin") || hasRole("super_admin")) && (
            <RouterLink to="/products">Products</RouterLink>
          )}
          {user && (hasRole("admin") || hasRole("super_admin")) && (
            <RouterLink to="/suppliers">Suppliers</RouterLink>
          )}
          {user && (hasRole("admin") || hasRole("super_admin")) && (
            <RouterLink to="/procurement-orders">Procurement</RouterLink>
          )}
          {user && hasRole("super_admin") && <RouterLink to="/regions">Regions</RouterLink>}
          {user && (hasRole("admin") || hasRole("super_admin") || hasRole("ambassador")) && (
            <RouterLink to="/buyer-groups">Buyer Groups</RouterLink>
          )}
          {user && (hasRole("admin") || hasRole("super_admin")) && (
            <RouterLink to="/seller-validation">Seller Validation</RouterLink>
          )}
          {user && hasRole("ambassador") && <RouterLink to="/ambassador">My Buyers</RouterLink>}
          {user && hasRole("super_admin") && <RouterLink to="/super-admin">Super Admin</RouterLink>}
        </nav>
        <div>
          {user ? (
            <>
              <span style={{ marginRight: 10 }}>{user.email}</span>
              <button
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                Logout
              </button>
            </>
          ) : null}
        </div>
      </header>
      <hr style={{ margin: "14px 0 22px" }} />
      {children}
    </div>
  );
}
