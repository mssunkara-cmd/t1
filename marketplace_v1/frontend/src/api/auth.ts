import { apiRequest } from "./client";
import type { AuthTokens, AuthUser, Region } from "../types/models";

type ProfilePayload = {
  first_name?: string;
  last_name?: string;
  address_line1?: string;
  address_line2?: string;
  address_line3?: string;
  zip_code?: string;
  phone_number?: string;
  region?: string;
  source_region_id?: number;
  major_distribution_region_id?: number;
};

export function login(email: string, password: string) {
  return apiRequest<AuthTokens>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function register(
  email: string,
  password: string,
  role: "buyer" | "seller",
  profile?: ProfilePayload
) {
  return apiRequest<AuthTokens>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, role, ...(profile ?? {}) })
  });
}

export function bootstrapAdmin(email: string, password: string, profile?: ProfilePayload) {
  return apiRequest<AuthTokens>("/auth/bootstrap-admin", {
    method: "POST",
    body: JSON.stringify({ email, password, ...(profile ?? {}) })
  });
}

export function getMe(token: string) {
  return apiRequest<AuthUser>("/auth/me", { method: "GET" }, token);
}

export function updateMyProfile(token: string, profile: ProfilePayload) {
  return apiRequest<AuthUser>(
    "/auth/me",
    {
      method: "PATCH",
      body: JSON.stringify(profile)
    },
    token
  );
}

export function listSourceRegions() {
  return apiRequest<{ items: Region[] }>("/auth/source-regions", { method: "GET" });
}

export function listMajorDistributionRegions() {
  return apiRequest<{ items: Region[] }>("/auth/major-distribution-regions", { method: "GET" });
}
