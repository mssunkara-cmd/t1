import { apiRequest } from "./client";
import type {
  InventoryItem,
  Pagination,
  ProcurementOrder,
  Product,
  ProductType,
  Region,
  Supplier,
  SupplierRating,
  UserRow
} from "../types/models";

export function listUsers(
  token: string,
  filters?: { role?: string; page?: number; page_size?: number }
) {
  const params = new URLSearchParams();
  if (filters?.role) params.set("role", filters.role);
  if (filters?.page) params.set("page", String(filters.page));
  if (filters?.page_size) params.set("page_size", String(filters.page_size));
  const query = params.toString();
  const path = query ? `/admin/users?${query}` : "/admin/users";

  return apiRequest<{ items: UserRow[]; pagination: Pagination }>(path, { method: "GET" }, token);
}

export async function listAllUsers(
  token: string,
  filters?: { role?: string }
): Promise<{ items: UserRow[] }> {
  const pageSize = 100;
  let page = 1;
  let totalPages = 1;
  const items: UserRow[] = [];

  while (page <= totalPages) {
    const response = await listUsers(token, {
      role: filters?.role,
      page,
      page_size: pageSize
    });
    items.push(...response.items);
    totalPages = response.pagination.total_pages || 1;
    page += 1;
  }

  return { items };
}

export function updateUserRoles(token: string, userId: number, roles: string[]) {
  return apiRequest<{ id: number; roles: string[] }>(
    `/admin/users/${userId}/roles`,
    {
      method: "POST",
      body: JSON.stringify({ roles })
    },
    token
  );
}

export function listInventory(
  token: string,
  filters?: {
    page?: number;
    page_size?: number;
    seller_id?: number;
    product_id?: number;
    product_type?: string;
    status?: "pending_validation" | "valid" | "rejected" | "active" | "inactive";
  }
) {
  const params = new URLSearchParams();
  if (filters?.page) params.set("page", String(filters.page));
  if (filters?.page_size) params.set("page_size", String(filters.page_size));
  if (filters?.seller_id) params.set("seller_id", String(filters.seller_id));
  if (filters?.product_id) params.set("product_id", String(filters.product_id));
  if (filters?.product_type) params.set("product_type", filters.product_type);
  if (filters?.status) params.set("status", filters.status);

  const query = params.toString();
  const path = query ? `/admin/inventory?${query}` : "/admin/inventory";
  return apiRequest<{ items: InventoryItem[]; pagination: Pagination }>(path, { method: "GET" }, token);
}

export function createInventoryItem(
  token: string,
  payload: { product_id: number; quantity: number; price_per_unit: string; seller_id?: number }
) {
  return apiRequest<InventoryItem>(
    "/admin/inventory",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function updateInventoryItem(
  token: string,
  itemId: number,
  quantity: number,
  pricePerUnit: string,
  inventoryKind?: "regular" | "fresh_produce"
) {
  const path = inventoryKind
    ? `/admin/inventory/${itemId}?inventory_kind=${encodeURIComponent(inventoryKind)}`
    : `/admin/inventory/${itemId}`;
  return apiRequest<InventoryItem>(
    path,
    {
      method: "PUT",
      body: JSON.stringify({ quantity, price_per_unit: pricePerUnit })
    },
    token
  );
}

export function deleteInventoryItem(token: string, itemId: number, inventoryKind?: "regular" | "fresh_produce") {
  const path = inventoryKind
    ? `/admin/inventory/${itemId}?inventory_kind=${encodeURIComponent(inventoryKind)}`
    : `/admin/inventory/${itemId}`;
  return apiRequest<{ message: string }>(path, { method: "DELETE" }, token);
}

export function listInventoryProductOptions(token: string) {
  return apiRequest<{ items: Product[] }>("/admin/inventory/product-options", { method: "GET" }, token);
}

export function listInventorySellerOptions(token: string) {
  return apiRequest<{ items: UserRow[] }>("/admin/inventory/seller-options", { method: "GET" }, token);
}

export function grantAdmin(token: string, userId: number) {
  return apiRequest<{ id: number; roles: string[] }>(
    `/admin/super-admin/users/${userId}/admin`,
    { method: "POST" },
    token
  );
}

export function revokeAdmin(token: string, userId: number) {
  return apiRequest<{ id: number; roles: string[] }>(
    `/admin/super-admin/users/${userId}/admin`,
    { method: "DELETE" },
    token
  );
}

export function grantAmbassador(token: string, userId: number) {
  return apiRequest<{ id: number; roles: string[] }>(
    `/admin/super-admin/users/${userId}/ambassador`,
    { method: "POST" },
    token
  );
}

export function revokeAmbassador(token: string, userId: number) {
  return apiRequest<{ id: number; roles: string[] }>(
    `/admin/super-admin/users/${userId}/ambassador`,
    { method: "DELETE" },
    token
  );
}

export function listAmbassadorBuyers(token: string, ambassadorUserId: number) {
  return apiRequest<{ items: UserRow[] }>(
    `/admin/ambassadors/${ambassadorUserId}/buyers`,
    { method: "GET" },
    token
  );
}

export function listBuyerGroupOptions(token: string, regionId?: number) {
  const params = new URLSearchParams();
  if (regionId) params.set("region_id", String(regionId));
  const query = params.toString();
  const path = query ? `/admin/buyer-groups/options?${query}` : "/admin/buyer-groups/options";

  return apiRequest<{
    owned_regions: Array<{
      region_id: number;
      region_name: string;
      distribution_level: "major" | "minor" | "local" | null;
      parent_region_id: number | null;
    }>;
    selected_region_id: number | null;
    ambassadors: UserRow[];
    buyers: UserRow[];
  }>(path, { method: "GET" }, token);
}

export function assignBuyerToAmbassador(token: string, ambassadorUserId: number, buyerUserId: number) {
  return apiRequest<{ message: string }>(
    `/admin/ambassadors/${ambassadorUserId}/buyers/${buyerUserId}`,
    { method: "POST" },
    token
  );
}

export function removeBuyerFromAmbassador(token: string, ambassadorUserId: number, buyerUserId: number) {
  return apiRequest<{ message: string }>(
    `/admin/ambassadors/${ambassadorUserId}/buyers/${buyerUserId}`,
    { method: "DELETE" },
    token
  );
}

export function setSellerStatus(
  token: string,
  userId: number,
  status: "pending_validation" | "valid" | "rejected"
) {
  return apiRequest<{ id: number; seller_status: string }>(
    `/admin/sellers/${userId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status })
    },
    token
  );
}

export function listSellerValidationQueue(token: string) {
  return apiRequest<{ items: UserRow[] }>("/admin/sellers/validation-queue", { method: "GET" }, token);
}

export function reassignSellerAdmin(token: string, sellerId: number, assignedAdminUserId: number) {
  return apiRequest<{ id: number; assigned_admin_user_id: number }>(
    `/admin/sellers/${sellerId}/assigned-admin`,
    {
      method: "PATCH",
      body: JSON.stringify({ assigned_admin_user_id: assignedAdminUserId })
    },
    token
  );
}

export function listProducts(token: string) {
  return apiRequest<{ items: Product[] }>("/admin/products", { method: "GET" }, token);
}

export function listProductTypes(token: string) {
  return apiRequest<{ items: ProductType[] }>("/admin/product-types", { method: "GET" }, token);
}

export function createProductType(token: string, payload: { product_type: string }) {
  return apiRequest<ProductType>(
    "/admin/product-types",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function deleteProductType(token: string, productTypeId: number) {
  return apiRequest<{ message: string }>(`/admin/product-types/${productTypeId}`, { method: "DELETE" }, token);
}

export function createProduct(
  token: string,
  payload: { product_name: string; product_type: string; product_unit: string; validity_days: number }
) {
  return apiRequest<Product>(
    "/admin/products",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function updateProduct(
  token: string,
  productId: number,
  payload: { product_name: string; product_type: string; product_unit: string; validity_days: number }
) {
  return apiRequest<Product>(
    `/admin/products/${productId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function deleteProduct(token: string, productId: number) {
  return apiRequest<{ message: string }>(`/admin/products/${productId}`, { method: "DELETE" }, token);
}

export function listSuppliers(token: string) {
  return apiRequest<{ items: Supplier[] }>("/admin/suppliers", { method: "GET" }, token);
}

export function listSupplierOptions(token: string) {
  return apiRequest<{
    items: Array<{ supplier_id: number; supplier_name: string; email?: string | null }>;
  }>("/admin/suppliers/options", { method: "GET" }, token);
}

export function createSupplier(
  token: string,
  payload: {
    supplier_name: string;
    email?: string;
    address_line1?: string;
    address_line2?: string;
    address_line3?: string;
    phone_number?: string;
    is_active: boolean;
    product_links: Array<{ product_id: number; supplier_type: "primary" | "secondary" | "reseller" }>;
  }
) {
  return apiRequest<Supplier>(
    "/admin/suppliers",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function updateSupplier(
  token: string,
  supplierId: number,
  payload: {
    supplier_name: string;
    email?: string;
    address_line1?: string;
    address_line2?: string;
    address_line3?: string;
    phone_number?: string;
    is_active: boolean;
    product_links: Array<{ product_id: number; supplier_type: "primary" | "secondary" | "reseller" }>;
  }
) {
  return apiRequest<Supplier>(
    `/admin/suppliers/${supplierId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function deleteSupplier(token: string, supplierId: number) {
  return apiRequest<{ message: string }>(`/admin/suppliers/${supplierId}`, { method: "DELETE" }, token);
}

export function getSupplierDetail(token: string, supplierId: number) {
  return apiRequest<{
    supplier_id: number;
    supplier_name: string;
    address_line1?: string | null;
    address_line2?: string | null;
    address_line3?: string | null;
    phone_number?: string | null;
    is_active: boolean;
    product_links: Array<{ product_id: number; supplier_type: "primary" | "secondary" | "reseller" }>;
    overall_rating?: number | null;
    rating_count?: number;
    rating_breakdown: Array<{ rating: number; orders: number }>;
    reviews: Array<{
      review_id: number;
      procurement_id: number;
      procurement_status?: string | null;
      rating: number;
      review_text?: string | null;
      created_at?: string | null;
    }>;
  }>(`/admin/suppliers/${supplierId}`, { method: "GET" }, token);
}

export function listProcurementOrders(
  token: string,
  filters?: {
    page?: number;
    page_size?: number;
    supplier_id?: number;
    product_id?: number;
    status?: "draft" | "placed" | "received" | "cancelled";
  }
) {
  const params = new URLSearchParams();
  if (filters?.page) params.set("page", String(filters.page));
  if (filters?.page_size) params.set("page_size", String(filters.page_size));
  if (filters?.supplier_id) params.set("supplier_id", String(filters.supplier_id));
  if (filters?.product_id) params.set("product_id", String(filters.product_id));
  if (filters?.status) params.set("status", filters.status);
  const query = params.toString();
  const path = query ? `/admin/procurement-orders?${query}` : "/admin/procurement-orders";

  return apiRequest<{ items: ProcurementOrder[]; pagination: Pagination }>(path, { method: "GET" }, token);
}

export function createProcurementOrder(
  token: string,
  payload: {
    supplier_id: number;
    product_id: number;
    quantity: number;
    price_per_unit: string;
    procurement_date?: string;
    status: "draft" | "placed" | "received" | "cancelled";
  }
) {
  return apiRequest<ProcurementOrder>(
    "/admin/procurement-orders",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function updateProcurementOrderStatus(
  token: string,
  procurementId: number,
  status: "draft" | "placed" | "received" | "cancelled"
) {
  return apiRequest<ProcurementOrder>(
    `/admin/procurement-orders/${procurementId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status })
    },
    token
  );
}

export function pushProcurementOrderToInventory(token: string, procurementId: number) {
  return apiRequest<{ message: string; inventory_item: InventoryItem }>(
    `/admin/procurement-orders/${procurementId}/push-to-inventory`,
    { method: "POST" },
    token
  );
}

export function listSupplierRatings(
  token: string,
  procurementId: number
) {
  return apiRequest<{ items: SupplierRating[] }>(
    `/admin/procurement-orders/${procurementId}/reviews`,
    { method: "GET" },
    token
  );
}

export function createSupplierRating(
  token: string,
  procurementId: number,
  payload: { rating: number; review_text?: string; images?: File[] }
) {
  const form = new FormData();
  form.append("rating", String(payload.rating));
  if (payload.review_text) {
    form.append("review_text", payload.review_text);
  }
  for (const image of payload.images ?? []) {
    form.append("images", image);
  }
  return apiRequest<SupplierRating>(
    `/admin/procurement-orders/${procurementId}/reviews`,
    {
      method: "POST",
      body: form
    },
    token
  );
}

export function listProcurementOrderOptions(token: string, includeDraft = false) {
  const params = new URLSearchParams();
  if (includeDraft) params.set("include_draft", "true");
  const query = params.toString();
  const path = query ? `/admin/procurement-orders/options?${query}` : "/admin/procurement-orders/options";
  return apiRequest<{ items: ProcurementOrder[] }>(path, { method: "GET" }, token);
}

export function listRegions(token: string) {
  return apiRequest<{ items: Region[] }>("/admin/regions", { method: "GET" }, token);
}

export function createRegion(
  token: string,
  payload: {
    region_name: string;
    region_description?: string;
    region_type: "source" | "distribution";
    distribution_level?: "major" | "minor" | "local";
    parent_region_id?: number;
  }
) {
  return apiRequest<Region>(
    "/admin/regions",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function updateRegion(
  token: string,
  regionId: number,
  payload: {
    region_name: string;
    region_description?: string;
    region_type: "source" | "distribution";
    distribution_level?: "major" | "minor" | "local";
    parent_region_id?: number;
  }
) {
  return apiRequest<Region>(
    `/admin/regions/${regionId}`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function deleteRegion(token: string, regionId: number) {
  return apiRequest<{ message: string }>(`/admin/regions/${regionId}`, { method: "DELETE" }, token);
}

export function setRegionDefaults(
  token: string,
  regionId: number,
  payload: { default_admin_user_id?: number; default_ambassador_user_id?: number }
) {
  return apiRequest<{
    region_id: number;
    default_admin_user_id: number | null;
    default_ambassador_user_id: number | null;
  }>(
    `/admin/regions/${regionId}/defaults`,
    {
      method: "PUT",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function regroupLocalRegions(
  token: string,
  payload: {
    major_region_id: number;
    new_minor_name: string;
    new_minor_description?: string;
    local_region_ids: number[];
  }
) {
  return apiRequest<{
    message: string;
    new_minor_region: Region;
    moved_local_region_ids: number[];
  }>(
    "/admin/regions/distribution/regroup-local",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}
