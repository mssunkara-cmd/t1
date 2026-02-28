import { useEffect, useMemo, useState } from "react";

import {
  listAllUsers,
  listSellerValidationQueue,
  reassignSellerAdmin,
  setSellerStatus
} from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { UserRow } from "../types/models";

export function SellerValidationPage() {
  const { accessToken, hasRole } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [allUsers, setAllUsers] = useState<UserRow[]>([]);
  const [adminSelectionBySeller, setAdminSelectionBySeller] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canManage = hasRole("admin") || hasRole("super_admin");
  const isSuperAdmin = hasRole("super_admin");

  const sellers = users;
  const adminCandidates = useMemo(
    () => allUsers.filter((u) => u.roles.includes("admin") || u.roles.includes("super_admin")),
    [allUsers]
  );

  const load = async () => {
    if (!accessToken || !canManage) {
      return;
    }
    try {
      const response = await listSellerValidationQueue(accessToken);
      setUsers(response.items);
      if (isSuperAdmin) {
        const usersResponse = await listAllUsers(accessToken);
        setAllUsers(usersResponse.items);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users");
    }
  };

  useEffect(() => {
    load();
  }, [accessToken, canManage, isSuperAdmin]);

  const updateStatus = async (sellerId: number, status: "pending_validation" | "valid" | "rejected") => {
    if (!accessToken) {
      return;
    }
    try {
      await setSellerStatus(accessToken, sellerId, status);
      setMessage(`Seller ${sellerId} marked as ${status}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update seller status");
    }
  };

  const reassignAdmin = async (sellerId: number) => {
    if (!accessToken) {
      return;
    }
    const value = adminSelectionBySeller[sellerId];
    if (!value) {
      setError("Please select an admin before reassigning.");
      return;
    }
    try {
      await reassignSellerAdmin(accessToken, sellerId, Number(value));
      setMessage(`Seller ${sellerId} reassigned to admin ${value}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reassign seller admin");
    }
  };

  return (
    <AppShell>
      <h1>Seller Validation</h1>
      {!canManage ? (
        <p>Only Admin or Super Admin can validate sellers.</p>
      ) : (
        <>
          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Seller ID</th>
                <th align="left">Email</th>
                <th align="left">Name</th>
                <th align="left">Status</th>
                <th align="left">Assigned Admin</th>
                <th align="left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sellers.map((seller) => (
                <tr key={seller.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{seller.id}</td>
                  <td>{seller.email}</td>
                  <td>{[seller.first_name, seller.last_name].filter(Boolean).join(" ") || "-"}</td>
                  <td>{seller.seller_status ?? "pending_validation"}</td>
                  <td>
                    {isSuperAdmin ? (
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <select
                          value={
                            adminSelectionBySeller[seller.id] ??
                            (seller.assigned_admin_user_id ? String(seller.assigned_admin_user_id) : "")
                          }
                          onChange={(e) =>
                            setAdminSelectionBySeller((prev) => ({
                              ...prev,
                              [seller.id]: e.target.value
                            }))
                          }
                        >
                          <option value="">Select Admin</option>
                          {adminCandidates.map((admin) => (
                            <option key={admin.id} value={String(admin.id)}>
                              {admin.id} - {admin.email}
                            </option>
                          ))}
                        </select>
                        <button onClick={() => reassignAdmin(seller.id)}>Reassign</button>
                      </div>
                    ) : (
                      seller.assigned_admin_user_id ?? "-"
                    )}
                  </td>
                  <td style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button onClick={() => updateStatus(seller.id, "valid")}>Mark Valid</button>
                    <button onClick={() => updateStatus(seller.id, "pending_validation")}>
                      Mark Pending
                    </button>
                    <button onClick={() => updateStatus(seller.id, "rejected")}>Reject</button>
                  </td>
                </tr>
              ))}
              {sellers.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={6}>No sellers found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
