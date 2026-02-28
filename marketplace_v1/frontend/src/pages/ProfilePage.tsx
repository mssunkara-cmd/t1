import { FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import { PROFILE_LIMITS, validateProfileFieldErrors } from "../utils/profileValidation";

export function ProfilePage() {
  const { user, accessToken, updateProfile } = useAuth();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [addressLine3, setAddressLine3] = useState("");
  const [zipCode, setZipCode] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [region, setRegion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

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
  const hasErrors = Object.keys(fieldErrors).length > 0;

  useEffect(() => {
    if (!user) {
      return;
    }
    setFirstName(user.first_name ?? "");
    setLastName(user.last_name ?? "");
    setAddressLine1(user.address_line1 ?? "");
    setAddressLine2(user.address_line2 ?? "");
    setAddressLine3(user.address_line3 ?? "");
    setZipCode(user.zip_code ?? "");
    setPhoneNumber(user.phone_number ?? "");
    setRegion(user.region ?? "");
  }, [user?.id]);

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken || !user) {
      return;
    }
    if (hasErrors) {
      return;
    }
    try {
      setError(null);
      setMessage(null);
      await updateProfile({
        first_name: firstName,
        last_name: lastName,
        address_line1: addressLine1,
        address_line2: addressLine2,
        address_line3: addressLine3,
        zip_code: zipCode,
        phone_number: phoneNumber,
        region
      });
      setMessage("Profile updated successfully.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update profile");
    }
  };

  return (
    <AppShell>
      <h1>My Profile</h1>
      {!user ? (
        <p>Please login first.</p>
      ) : (
        <>
          <p>Email (login name): <strong>{user.email}</strong> (read-only)</p>
          <form onSubmit={saveProfile} style={{ display: "grid", gap: 10, maxWidth: 460 }}>
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
            <button type="submit" disabled={hasErrors}>Save Profile</button>
          </form>
          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}
        </>
      )}
    </AppShell>
  );
}
