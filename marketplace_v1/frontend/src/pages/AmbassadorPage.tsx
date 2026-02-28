import { useEffect, useState } from "react";

import { listAmbassadorBuyers } from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { UserRow } from "../types/models";

export function AmbassadorPage() {
  const { user, accessToken, hasRole } = useAuth();
  const [buyers, setBuyers] = useState<UserRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!user || !accessToken) {
      return;
    }
    try {
      const data = await listAmbassadorBuyers(accessToken, user.id);
      setBuyers(data.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load buyers");
    }
  };

  useEffect(() => {
    if (hasRole("ambassador")) {
      load();
    }
  }, [user?.id, accessToken]);

  return (
    <AppShell>
      <h1>Ambassador Buyer Group</h1>
      {!hasRole("ambassador") ? (
        <p>Ambassador role is required.</p>
      ) : (
        <>
          {error && <p style={{ color: "crimson" }}>{error}</p>}
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Buyer ID</th>
                <th align="left">Email</th>
                <th align="left">Name</th>
                <th align="left">Phone</th>
                <th align="left">Region</th>
              </tr>
            </thead>
            <tbody>
              {buyers.map((buyer) => (
                <tr key={buyer.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{buyer.id}</td>
                  <td>{buyer.email}</td>
                  <td>{[buyer.first_name, buyer.last_name].filter(Boolean).join(" ") || "-"}</td>
                  <td>{buyer.phone_number ?? "-"}</td>
                  <td>{buyer.region ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
