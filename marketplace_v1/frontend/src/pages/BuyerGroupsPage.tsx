import { useEffect, useMemo, useState } from "react";

import {
  assignBuyerToAmbassador,
  listBuyerGroupOptions,
  listAmbassadorBuyers,
  removeBuyerFromAmbassador
} from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { UserRow } from "../types/models";

export function BuyerGroupsPage() {
  const { accessToken, hasRole, user } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [ownedRegions, setOwnedRegions] = useState<
    Array<{
      region_id: number;
      region_name: string;
      distribution_level: "major" | "minor" | "local" | null;
      parent_region_id: number | null;
    }>
  >([]);
  const [selectedOwnedRegionId, setSelectedOwnedRegionId] = useState("");
  const [selectedAmbassadorId, setSelectedAmbassadorId] = useState("");
  const [selectedBuyerId, setSelectedBuyerId] = useState("");
  const [assignedBuyers, setAssignedBuyers] = useState<UserRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canManage = hasRole("admin") || hasRole("super_admin") || hasRole("ambassador");
  const isAdminLike = hasRole("admin") || hasRole("super_admin");
  const isAmbassadorOnly = hasRole("ambassador") && !isAdminLike;

  const ambassadors = useMemo(
    () => users.filter((u) => u.roles.includes("ambassador")),
    [users]
  );

  const buyers = useMemo(
    () => users.filter((u) => u.roles.includes("buyer")),
    [users]
  );
  const selectedOwnedRegion = useMemo(
    () => ownedRegions.find((r) => String(r.region_id) === selectedOwnedRegionId) ?? null,
    [ownedRegions, selectedOwnedRegionId]
  );
  const scopeSummary = useMemo(() => {
    if (!isAmbassadorOnly || !selectedOwnedRegion) {
      return null;
    }
    const level = selectedOwnedRegion.distribution_level ?? "distribution";
    if (level === "major") {
      return `Major region scope: showing ${ambassadors.length} ambassadors and ${buyers.length} buyers in this major distribution region.`;
    }
    if (level === "minor") {
      return `Minor region scope: showing ${ambassadors.length} local ambassadors and ${buyers.length} buyers that are not assigned to local ambassadors.`;
    }
    if (level === "local") {
      return `Local region scope: showing your local assignments. Visible buyers: ${buyers.length}.`;
    }
    return `Region scope: showing ${ambassadors.length} ambassadors and ${buyers.length} buyers.`;
  }, [isAmbassadorOnly, selectedOwnedRegion, ambassadors.length, buyers.length]);

  const loadUsers = async () => {
    if (!accessToken || !canManage) {
      return;
    }
    try {
      const regionId = selectedOwnedRegionId ? Number(selectedOwnedRegionId) : undefined;
      const response = await listBuyerGroupOptions(accessToken, regionId);
      const merged = [...response.ambassadors, ...response.buyers];
      setUsers(merged);
      setOwnedRegions(response.owned_regions ?? []);
      if (response.selected_region_id) {
        setSelectedOwnedRegionId(String(response.selected_region_id));
      }
      if (isAmbassadorOnly) {
        if (response.ambassadors.length > 0) {
          const selfId = user?.id ?? 0;
          const hasSelf = response.ambassadors.some((u) => u.id === selfId);
          setSelectedAmbassadorId(hasSelf ? String(selfId) : String(response.ambassadors[0].id));
        } else {
          setSelectedAmbassadorId("");
        }
      }
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users");
    }
  };

  const loadGroup = async (ambassadorId: number) => {
    if (!accessToken) {
      return;
    }
    try {
      const response = await listAmbassadorBuyers(accessToken, ambassadorId);
      setAssignedBuyers(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load ambassador group");
    }
  };

  useEffect(() => {
    loadUsers();
  }, [accessToken, canManage, selectedOwnedRegionId, user?.id]);

  useEffect(() => {
    if (!selectedAmbassadorId) {
      setAssignedBuyers([]);
      return;
    }
    loadGroup(Number(selectedAmbassadorId));
  }, [selectedAmbassadorId]);

  const assignBuyer = async () => {
    if (!accessToken || !selectedAmbassadorId || !selectedBuyerId) {
      return;
    }
    try {
      await assignBuyerToAmbassador(accessToken, Number(selectedAmbassadorId), Number(selectedBuyerId));
      setMessage("Buyer assigned to ambassador.");
      await loadGroup(Number(selectedAmbassadorId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to assign buyer");
    }
  };

  const removeBuyer = async () => {
    if (!accessToken || !selectedAmbassadorId || !selectedBuyerId) {
      return;
    }
    try {
      await removeBuyerFromAmbassador(accessToken, Number(selectedAmbassadorId), Number(selectedBuyerId));
      setMessage("Buyer removed from ambassador.");
      await loadGroup(Number(selectedAmbassadorId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove buyer");
    }
  };

  return (
    <AppShell>
      <h1>Buyer Group Management</h1>
      {!canManage ? (
        <p>Admin, Super Admin, or Ambassador role is required.</p>
      ) : (
        <>
          {scopeSummary ? (
            <div
              style={{
                marginBottom: 12,
                padding: "10px 12px",
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                borderRadius: 6
              }}
            >
              {scopeSummary}
            </div>
          ) : null}
          <div style={{ display: "grid", gap: 8, maxWidth: 520 }}>
            {isAmbassadorOnly && ownedRegions.length > 0 ? (
              <label>
                My Region Scope
                <select
                  value={selectedOwnedRegionId}
                  onChange={(e) => {
                    setSelectedOwnedRegionId(e.target.value);
                    setSelectedBuyerId("");
                    setAssignedBuyers([]);
                    setMessage(null);
                  }}
                  style={{ display: "block", width: "100%" }}
                >
                  {ownedRegions.map((region) => (
                    <option key={region.region_id} value={String(region.region_id)}>
                      {region.region_name} ({region.distribution_level ?? "distribution"})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <label>
              Ambassador
              <select
                value={selectedAmbassadorId}
                onChange={(e) => {
                  setSelectedAmbassadorId(e.target.value);
                  setMessage(null);
                }}
                style={{ display: "block", width: "100%" }}
              >
                <option value="">Select ambassador</option>
                {ambassadors.map((amb) => (
                  <option key={amb.id} value={String(amb.id)}>
                    {amb.id} - {amb.email}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Buyer
              <select
                value={selectedBuyerId}
                onChange={(e) => {
                  setSelectedBuyerId(e.target.value);
                  setMessage(null);
                }}
                style={{ display: "block", width: "100%" }}
              >
                <option value="">Select buyer</option>
                {buyers.map((buyer) => (
                  <option key={buyer.id} value={String(buyer.id)}>
                    {buyer.id} - {buyer.email}
                  </option>
                ))}
              </select>
            </label>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button onClick={assignBuyer} disabled={!selectedAmbassadorId || !selectedBuyerId}>
                Assign Buyer
              </button>
              <button onClick={removeBuyer} disabled={!selectedAmbassadorId || !selectedBuyerId}>
                Remove Buyer
              </button>
            </div>
          </div>

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <h3 style={{ marginTop: 22 }}>Assigned Buyers</h3>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Buyer ID</th>
                <th align="left">Email</th>
                <th align="left">Name</th>
                <th align="left">Region</th>
              </tr>
            </thead>
            <tbody>
              {assignedBuyers.map((buyer) => (
                <tr key={buyer.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{buyer.id}</td>
                  <td>{buyer.email}</td>
                  <td>{[buyer.first_name, buyer.last_name].filter(Boolean).join(" ") || "-"}</td>
                  <td>{buyer.region ?? "-"}</td>
                </tr>
              ))}
              {selectedAmbassadorId && assignedBuyers.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={4}>No buyers assigned yet.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
