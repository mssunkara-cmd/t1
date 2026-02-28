import { useEffect, useState } from "react";

import { grantAdmin, grantAmbassador, listUsers, revokeAdmin, revokeAmbassador } from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Pagination, UserRow } from "../types/models";

export function SuperAdminPage() {
  const { accessToken, hasRole, user } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [roleFilter, setRoleFilter] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0
  });
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!accessToken) {
      return;
    }
    try {
      const data = await listUsers(accessToken, {
        role: roleFilter || undefined,
        page,
        page_size: pageSize
      });
      setUsers(data.items);
      setPagination(data.pagination);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users");
    }
  };

  useEffect(() => {
    if (hasRole("super_admin")) {
      load();
    }
  }, [accessToken, user?.id, roleFilter, page, pageSize]);

  const makeAdmin = async (id: number) => {
    if (!accessToken) {
      return;
    }
    try {
      await grantAdmin(accessToken, id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to grant admin");
    }
  };

  const removeAdmin = async (id: number) => {
    if (!accessToken) {
      return;
    }
    try {
      await revokeAdmin(accessToken, id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to revoke admin");
    }
  };

  const makeAmbassador = async (id: number) => {
    if (!accessToken) {
      return;
    }
    try {
      await grantAmbassador(accessToken, id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to grant ambassador");
    }
  };

  const removeAmbassador = async (id: number) => {
    if (!accessToken) {
      return;
    }
    try {
      await revokeAmbassador(accessToken, id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to revoke ambassador");
    }
  };

  return (
    <AppShell>
      <h1>Super Admin</h1>
      {!hasRole("super_admin") ? (
        <p>Super Admin role is required.</p>
      ) : (
        <>
          {error && <p style={{ color: "crimson" }}>{error}</p>}
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <select value={roleFilter} onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}>
              <option value="">All Roles</option>
              <option value="super_admin">super_admin</option>
              <option value="admin">admin</option>
              <option value="ambassador">ambassador</option>
              <option value="seller">seller</option>
              <option value="buyer">buyer</option>
              <option value="support_ops">support_ops</option>
            </select>
            <select value={String(pageSize)} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              <option value="10">10 / page</option>
              <option value="20">20 / page</option>
              <option value="50">50 / page</option>
            </select>
          </div>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Email</th>
                <th align="left">Roles</th>
                <th align="left">Admin Access</th>
                <th align="left">Ambassador Access</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isAdmin = u.roles.includes("admin");
                const isAmbassador = u.roles.includes("ambassador");
                return (
                  <tr key={u.id} style={{ borderTop: "1px solid #ddd" }}>
                    <td>{u.email}</td>
                    <td>{u.roles.join(", ")}</td>
                    <td>
                      {isAdmin ? (
                        <button onClick={() => removeAdmin(u.id)}>Revoke Admin</button>
                      ) : (
                        <button onClick={() => makeAdmin(u.id)}>Grant Admin</button>
                      )}
                    </td>
                    <td>
                      {isAmbassador ? (
                        <button onClick={() => removeAmbassador(u.id)}>Revoke Ambassador</button>
                      ) : (
                        <button onClick={() => makeAmbassador(u.id)}>Grant Ambassador</button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={pagination.page <= 1}>
              Previous
            </button>
            <span>
              Page {pagination.page} / {Math.max(1, pagination.total_pages)} (Total {pagination.total})
            </span>
            <button
              onClick={() =>
                setPage((p) => (pagination.total_pages ? Math.min(p + 1, pagination.total_pages) : p + 1))
              }
              disabled={pagination.total_pages > 0 ? pagination.page >= pagination.total_pages : true}
            >
              Next
            </button>
          </div>
        </>
      )}
    </AppShell>
  );
}
