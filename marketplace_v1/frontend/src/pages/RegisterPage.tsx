import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../app/auth";
import { listMajorDistributionRegions, listSourceRegions } from "../api/auth";
import { ApiError } from "../api/client";
import { AppShell } from "../components/layout/AppShell";
import type { Region } from "../types/models";
import { PROFILE_LIMITS, validateProfileFieldErrors } from "../utils/profileValidation";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"buyer" | "seller">("buyer");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [addressLine3, setAddressLine3] = useState("");
  const [zipCode, setZipCode] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [region, setRegion] = useState("");
  const [sourceRegionId, setSourceRegionId] = useState("");
  const [sourceRegions, setSourceRegions] = useState<Region[]>([]);
  const [majorDistributionRegionId, setMajorDistributionRegionId] = useState("");
  const [majorDistributionRegions, setMajorDistributionRegions] = useState<Region[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const profileValues = useMemo(
    () => ({
      first_name: firstName,
      last_name: lastName,
      address_line1: addressLine1,
      address_line2: addressLine2,
      address_line3: addressLine3,
      zip_code: zipCode,
      phone_number: phoneNumber,
      region
    }),
    [firstName, lastName, addressLine1, addressLine2, addressLine3, zipCode, phoneNumber, region]
  );

  const fieldErrors = useMemo(() => validateProfileFieldErrors(profileValues), [profileValues]);
  const emailError = email.trim() ? null : "Email is required.";
  const passwordError = password.trim() ? null : "Password is required.";
  const sourceRegionError =
    role === "seller" && !sourceRegionId ? "Source Region is required for seller registration." : null;
  const majorDistributionRegionError =
    role === "buyer" && !majorDistributionRegionId
      ? "Major Distribution Region is required for buyer registration."
      : null;
  const hasErrors = Boolean(
    emailError ||
    passwordError ||
    sourceRegionError ||
    majorDistributionRegionError ||
    Object.keys(fieldErrors).length > 0
  );

  useEffect(() => {
    const loadRegionOptions = async () => {
      try {
        const [sourceResponse, majorResponse] = await Promise.all([
          listSourceRegions(),
          listMajorDistributionRegions()
        ]);
        setSourceRegions(sourceResponse.items);
        setMajorDistributionRegions(majorResponse.items);
      } catch {
        setSourceRegions([]);
        setMajorDistributionRegions([]);
      }
    };
    loadRegionOptions();
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (hasErrors) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await register(email, password, role, {
        first_name: firstName,
        last_name: lastName,
        address_line1: addressLine1,
        address_line2: addressLine2,
        address_line3: addressLine3,
        zip_code: zipCode,
        phone_number: phoneNumber,
        ...(sourceRegionId ? { source_region_id: Number(sourceRegionId) } : {}),
        ...(majorDistributionRegionId
          ? { major_distribution_region_id: Number(majorDistributionRegionId) }
          : {}),
        region
      });
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell>
      <h1>Register</h1>
      <form onSubmit={submit} style={{ display: "grid", gap: 10, maxWidth: 360 }}>
        <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        {emailError && <small style={{ color: "crimson" }}>{emailError}</small>}
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {passwordError && <small style={{ color: "crimson" }}>{passwordError}</small>}
        <input
          placeholder="First Name"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          maxLength={PROFILE_LIMITS.first_name}
        />
        {fieldErrors.first_name && <small style={{ color: "crimson" }}>{fieldErrors.first_name}</small>}
        <input
          placeholder="Last Name"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          maxLength={PROFILE_LIMITS.last_name}
        />
        {fieldErrors.last_name && <small style={{ color: "crimson" }}>{fieldErrors.last_name}</small>}
        <input
          placeholder="Address Line 1"
          value={addressLine1}
          onChange={(e) => setAddressLine1(e.target.value)}
          maxLength={PROFILE_LIMITS.address_line1}
        />
        {fieldErrors.address_line1 && (
          <small style={{ color: "crimson" }}>{fieldErrors.address_line1}</small>
        )}
        <input
          placeholder="Address Line 2"
          value={addressLine2}
          onChange={(e) => setAddressLine2(e.target.value)}
          maxLength={PROFILE_LIMITS.address_line2}
        />
        {fieldErrors.address_line2 && (
          <small style={{ color: "crimson" }}>{fieldErrors.address_line2}</small>
        )}
        <input
          placeholder="Address Line 3"
          value={addressLine3}
          onChange={(e) => setAddressLine3(e.target.value)}
          maxLength={PROFILE_LIMITS.address_line3}
        />
        {fieldErrors.address_line3 && (
          <small style={{ color: "crimson" }}>{fieldErrors.address_line3}</small>
        )}
        <input
          placeholder="Zip Code"
          value={zipCode}
          onChange={(e) => setZipCode(e.target.value)}
          maxLength={PROFILE_LIMITS.zip_code}
        />
        {fieldErrors.zip_code && <small style={{ color: "crimson" }}>{fieldErrors.zip_code}</small>}
        <input
          placeholder="Phone Number"
          value={phoneNumber}
          onChange={(e) => setPhoneNumber(e.target.value)}
          maxLength={PROFILE_LIMITS.phone_number}
        />
        {fieldErrors.phone_number && (
          <small style={{ color: "crimson" }}>{fieldErrors.phone_number}</small>
        )}
        <input
          placeholder="Region"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          maxLength={PROFILE_LIMITS.region}
        />
        {fieldErrors.region && <small style={{ color: "crimson" }}>{fieldErrors.region}</small>}
        <select value={role} onChange={(e) => setRole(e.target.value as "buyer" | "seller")}>
          <option value="buyer">Buyer</option>
          <option value="seller">Seller</option>
        </select>
        {role === "buyer" ? (
          <>
            <select
              value={majorDistributionRegionId}
              onChange={(e) => setMajorDistributionRegionId(e.target.value)}
            >
              <option value="">Select Major Distribution Region</option>
              {majorDistributionRegions.map((r) => (
                <option key={r.region_id} value={String(r.region_id)}>
                  {r.region_name}
                </option>
              ))}
            </select>
            {majorDistributionRegionError && (
              <small style={{ color: "crimson" }}>{majorDistributionRegionError}</small>
            )}
          </>
        ) : null}
        {role === "seller" ? (
          <>
            <select value={sourceRegionId} onChange={(e) => setSourceRegionId(e.target.value)}>
              <option value="">Select Source Region</option>
              {sourceRegions.map((r) => (
                <option key={r.region_id} value={String(r.region_id)}>
                  {r.region_name}
                </option>
              ))}
            </select>
            {sourceRegionError && <small style={{ color: "crimson" }}>{sourceRegionError}</small>}
          </>
        ) : null}
        <button type="submit" disabled={busy || hasErrors}>Create Account</button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </AppShell>
  );
}
