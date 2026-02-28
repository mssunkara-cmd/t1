import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createRegion,
  deleteRegion,
  listAllUsers,
  listRegions,
  regroupLocalRegions,
  setRegionDefaults,
  updateRegion
} from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Region, UserRow } from "../types/models";

export function RegionsPage() {
  const { accessToken, hasRole } = useAuth();
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionName, setRegionName] = useState("");
  const [regionDescription, setRegionDescription] = useState("");
  const [regionType, setRegionType] = useState<"source" | "distribution">("source");
  const [distributionLevel, setDistributionLevel] = useState<"major" | "minor" | "local" | "">("");
  const [parentRegionId, setParentRegionId] = useState("");
  const [editingRegionId, setEditingRegionId] = useState<number | null>(null);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [selectedRegionIdForDefaults, setSelectedRegionIdForDefaults] = useState("");
  const [defaultAdminUserId, setDefaultAdminUserId] = useState("");
  const [defaultAmbassadorUserId, setDefaultAmbassadorUserId] = useState("");
  const [selectedMajorRegionIdForRegroup, setSelectedMajorRegionIdForRegroup] = useState("");
  const [selectedLocalRegionIds, setSelectedLocalRegionIds] = useState<string[]>([]);
  const [newMinorName, setNewMinorName] = useState("");
  const [newMinorDescription, setNewMinorDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canManage = hasRole("super_admin");

  const regionById = useMemo(
    () => new Map<number, Region>(regions.map((region) => [region.region_id, region])),
    [regions]
  );

  const majorDistributionRegions = useMemo(
    () =>
      regions.filter(
        (r) => r.region_type === "distribution" && r.distribution_level === "major"
      ),
    [regions]
  );

  const minorDistributionRegions = useMemo(
    () =>
      regions.filter(
        (r) => r.region_type === "distribution" && r.distribution_level === "minor"
      ),
    [regions]
  );

  const localDistributionRegions = useMemo(
    () =>
      regions.filter(
        (r) => r.region_type === "distribution" && r.distribution_level === "local"
      ),
    [regions]
  );

  const getMajorRegionId = (region: Region): number | null => {
    if (region.region_type !== "distribution") return null;
    if (region.distribution_level === "major") return region.region_id;
    if (region.distribution_level === "minor") return region.parent_region_id ?? null;

    if (region.distribution_level === "local" && region.parent_region_id) {
      const minor = regionById.get(region.parent_region_id);
      if (minor?.distribution_level === "minor") {
        return minor.parent_region_id ?? null;
      }
    }
    return null;
  };

  const load = async () => {
    if (!accessToken || !canManage) {
      return;
    }
    try {
      const response = await listRegions(accessToken);
      setRegions(response.items);
      const usersResponse = await listAllUsers(accessToken);
      setUsers(usersResponse.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load regions");
    }
  };

  useEffect(() => {
    load();
  }, [accessToken, canManage]);

  const resetForm = () => {
    setEditingRegionId(null);
    setRegionName("");
    setRegionDescription("");
    setRegionType("source");
    setDistributionLevel("");
    setParentRegionId("");
  };

  const validate = () => {
    if (!regionName.trim()) {
      return "Region Name is required.";
    }
    if (regionName.length > 150) {
      return "Region Name max length is 150.";
    }
    if (regionDescription.length > 1500) {
      return "Region Description max length is 1500.";
    }
    if (!regionType) {
      return "Region Type is required.";
    }

    if (regionType === "distribution") {
      if (!distributionLevel) {
        return "Distribution Level is required for distribution regions.";
      }
      if (distributionLevel === "major" && parentRegionId) {
        return "Major distribution region cannot have a parent.";
      }
      if ((distributionLevel === "minor" || distributionLevel === "local") && !parentRegionId) {
        return "Parent Region is required for minor/local distribution regions.";
      }
    }

    return null;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken) {
      return;
    }

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    const payload = {
      region_name: regionName,
      region_description: regionDescription,
      region_type: regionType,
      ...(regionType === "distribution" && distributionLevel
        ? { distribution_level: distributionLevel }
        : {}),
      ...(regionType === "distribution" && parentRegionId ? { parent_region_id: Number(parentRegionId) } : {})
    };

    try {
      setError(null);
      if (editingRegionId) {
        await updateRegion(accessToken, editingRegionId, payload);
        setMessage("Region updated.");
      } else {
        await createRegion(accessToken, payload);
        setMessage("Region created.");
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save region");
    }
  };

  const startEdit = (region: Region) => {
    setEditingRegionId(region.region_id);
    setRegionName(region.region_name);
    setRegionDescription(region.region_description ?? "");
    setRegionType(region.region_type);
    setDistributionLevel(region.distribution_level ?? "");
    setParentRegionId(region.parent_region_id ? String(region.parent_region_id) : "");
  };

  const remove = async (regionId: number) => {
    if (!accessToken) {
      return;
    }
    try {
      await deleteRegion(accessToken, regionId);
      setMessage("Region deleted.");
      if (editingRegionId === regionId) {
        resetForm();
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete region");
    }
  };

  const selectedRegion = regions.find((r) => String(r.region_id) == selectedRegionIdForDefaults);
  const adminCandidates = users.filter((u) => u.roles.includes("admin") || u.roles.includes("super_admin"));
  const ambassadorCandidates = users.filter((u) => u.roles.includes("ambassador"));

  const applyDefaults = async () => {
    if (!accessToken || !selectedRegion) {
      return;
    }
    try {
      if (selectedRegion.region_type === "source") {
        if (!defaultAdminUserId) {
          setError("Select default admin user.");
          return;
        }
        await setRegionDefaults(accessToken, selectedRegion.region_id, {
          default_admin_user_id: Number(defaultAdminUserId)
        });
      } else if (selectedRegion.region_type === "distribution") {
        if (!defaultAmbassadorUserId) {
          setError("Select default ambassador user.");
          return;
        }
        await setRegionDefaults(accessToken, selectedRegion.region_id, {
          default_ambassador_user_id: Number(defaultAmbassadorUserId)
        });
      } else {
        setError("Defaults are supported only for source and major distribution regions.");
        return;
      }
      setMessage("Region defaults updated.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update region defaults");
    }
  };

  const parentOptions = useMemo(() => {
    if (regionType !== "distribution") return [] as Region[];
    if (distributionLevel === "minor") return majorDistributionRegions;
    if (distributionLevel === "local") return minorDistributionRegions;
    return [] as Region[];
  }, [regionType, distributionLevel, majorDistributionRegions, minorDistributionRegions]);

  const availableLocalsForRegroup = useMemo(() => {
    if (!selectedMajorRegionIdForRegroup) return [] as Region[];
    const majorId = Number(selectedMajorRegionIdForRegroup);
    return localDistributionRegions.filter((r) => getMajorRegionId(r) === majorId);
  }, [selectedMajorRegionIdForRegroup, localDistributionRegions, regionById]);

  const runRegroup = async () => {
    if (!accessToken) return;
    if (!selectedMajorRegionIdForRegroup) {
      setError("Select major distribution region for regroup.");
      return;
    }
    if (!newMinorName.trim()) {
      setError("New minor region name is required.");
      return;
    }
    if (!selectedLocalRegionIds.length) {
      setError("Select at least one local region.");
      return;
    }

    try {
      setError(null);
      await regroupLocalRegions(accessToken, {
        major_region_id: Number(selectedMajorRegionIdForRegroup),
        new_minor_name: newMinorName,
        new_minor_description: newMinorDescription,
        local_region_ids: selectedLocalRegionIds.map(Number)
      });
      setMessage("Created new minor region and regrouped local regions.");
      setNewMinorName("");
      setNewMinorDescription("");
      setSelectedLocalRegionIds([]);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to regroup local regions");
    }
  };

  return (
    <AppShell>
      <h1>Regions</h1>
      {!canManage ? (
        <p>Only Super Admin can manage regions.</p>
      ) : (
        <>
          <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 720, marginBottom: 16 }}>
            <input
              placeholder="Region Name"
              value={regionName}
              onChange={(e) => setRegionName(e.target.value)}
              maxLength={150}
            />
            <textarea
              placeholder="Region Description"
              value={regionDescription}
              onChange={(e) => setRegionDescription(e.target.value)}
              maxLength={1500}
              rows={4}
            />
            <select
              value={regionType}
              onChange={(e) => {
                const value = e.target.value as "source" | "distribution";
                setRegionType(value);
                if (value === "source") {
                  setDistributionLevel("");
                  setParentRegionId("");
                }
              }}
            >
              <option value="source">source</option>
              <option value="distribution">distribution</option>
            </select>

            {regionType === "distribution" ? (
              <>
                <select
                  value={distributionLevel}
                  onChange={(e) => {
                    const level = e.target.value as "major" | "minor" | "local" | "";
                    setDistributionLevel(level);
                    setParentRegionId("");
                  }}
                >
                  <option value="">Select Distribution Level</option>
                  <option value="major">major</option>
                  <option value="minor">minor</option>
                  <option value="local">local</option>
                </select>

                {distributionLevel === "minor" || distributionLevel === "local" ? (
                  <select value={parentRegionId} onChange={(e) => setParentRegionId(e.target.value)}>
                    <option value="">Select Parent Region</option>
                    {parentOptions.map((region) => (
                      <option key={region.region_id} value={String(region.region_id)}>
                        {region.region_name} ({region.distribution_level})
                      </option>
                    ))}
                  </select>
                ) : null}
              </>
            ) : null}

            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit">{editingRegionId ? "Update Region" : "Create Region"}</button>
              {editingRegionId ? (
                <button type="button" onClick={resetForm}>
                  Cancel Edit
                </button>
              ) : null}
            </div>
          </form>

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">ID</th>
                <th align="left">Name</th>
                <th align="left">Type</th>
                <th align="left">Level</th>
                <th align="left">Parent</th>
                <th align="left">Description</th>
                <th align="left">Default Admin</th>
                <th align="left">Default Ambassador</th>
                <th align="left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {regions.map((region) => (
                <tr key={region.region_id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{region.region_id}</td>
                  <td>{region.region_name}</td>
                  <td>{region.region_type}</td>
                  <td>{region.distribution_level ?? "-"}</td>
                  <td>{region.parent_region_name ?? region.parent_region_id ?? "-"}</td>
                  <td>{region.region_description ?? "-"}</td>
                  <td>{region.default_admin_user_id ?? "-"}</td>
                  <td>{region.default_ambassador_user_id ?? "-"}</td>
                  <td style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => startEdit(region)}>Edit</button>
                    <button onClick={() => remove(region.region_id)}>Delete</button>
                  </td>
                </tr>
              ))}
              {regions.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={9}>No regions found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>

          <hr style={{ margin: "18px 0" }} />
      <h3>Region Defaults</h3>
          <div style={{ display: "grid", gap: 8, maxWidth: 520 }}>
            <select
              value={selectedRegionIdForDefaults}
              onChange={(e) => {
                const regionId = e.target.value;
                setSelectedRegionIdForDefaults(regionId);
                const region = regions.find((r) => String(r.region_id) === regionId);
                setDefaultAdminUserId(region?.default_admin_user_id ? String(region.default_admin_user_id) : "");
                setDefaultAmbassadorUserId(
                  region?.default_ambassador_user_id ? String(region.default_ambassador_user_id) : ""
                );
              }}
            >
              <option value="">Select Region</option>
              {regions.map((region) => (
                <option key={region.region_id} value={String(region.region_id)}>
                  {region.region_name} ({region.region_type}
                  {region.distribution_level ? `/${region.distribution_level}` : ""})
                </option>
              ))}
            </select>

            {selectedRegion?.region_type === "source" ? (
              <select value={defaultAdminUserId} onChange={(e) => setDefaultAdminUserId(e.target.value)}>
                <option value="">Select Default Admin</option>
                {adminCandidates.map((user) => (
                  <option key={user.id} value={String(user.id)}>
                    {user.id} - {user.email}
                  </option>
                ))}
              </select>
            ) : null}

            {selectedRegion?.region_type === "distribution" ? (
              <select
                value={defaultAmbassadorUserId}
                onChange={(e) => setDefaultAmbassadorUserId(e.target.value)}
              >
                <option value="">Select Default Ambassador</option>
                {ambassadorCandidates.map((user) => (
                  <option key={user.id} value={String(user.id)}>
                    {user.id} - {user.email}
                  </option>
                ))}
              </select>
            ) : null}

            <button type="button" onClick={applyDefaults} disabled={!selectedRegion}>
              Save Region Defaults
            </button>
          </div>

          <hr style={{ margin: "18px 0" }} />
          <h3>Distribution Rebalance (Local → New Minor)</h3>
          <div style={{ display: "grid", gap: 8, maxWidth: 720 }}>
            <select
              value={selectedMajorRegionIdForRegroup}
              onChange={(e) => {
                setSelectedMajorRegionIdForRegroup(e.target.value);
                setSelectedLocalRegionIds([]);
              }}
            >
              <option value="">Select Major Distribution Region</option>
              {majorDistributionRegions.map((region) => (
                <option key={region.region_id} value={String(region.region_id)}>
                  {region.region_name}
                </option>
              ))}
            </select>

            <input
              placeholder="New Minor Region Name"
              value={newMinorName}
              onChange={(e) => setNewMinorName(e.target.value)}
              maxLength={150}
            />
            <textarea
              placeholder="New Minor Region Description"
              value={newMinorDescription}
              onChange={(e) => setNewMinorDescription(e.target.value)}
              maxLength={1500}
              rows={3}
            />

            <select
              multiple
              value={selectedLocalRegionIds}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions).map((option) => option.value);
                setSelectedLocalRegionIds(values);
              }}
              size={Math.max(4, Math.min(10, availableLocalsForRegroup.length))}
            >
              {availableLocalsForRegroup.map((region) => (
                <option key={region.region_id} value={String(region.region_id)}>
                  {region.region_name} (id: {region.region_id})
                </option>
              ))}
            </select>

            <button type="button" onClick={runRegroup}>
              Create Minor Region and Move Selected Locals
            </button>
          </div>
        </>
      )}
    </AppShell>
  );
}
