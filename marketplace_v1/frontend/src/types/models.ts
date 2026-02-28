export type AuthUser = {
  id: number;
  email: string;
  roles: string[];
  first_name?: string | null;
  last_name?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  address_line3?: string | null;
  zip_code?: string | null;
  phone_number?: string | null;
  region?: string | null;
  source_region_id?: number | null;
  major_distribution_region_id?: number | null;
  seller_status?: string | null;
  assigned_admin_user_id?: number | null;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
};

export type OrderItem = {
  id?: number;
  sku: string;
  name: string;
  qty: number;
  unit_price: string;
};

export type Order = {
  id: number;
  order_number: string;
  buyer_id: number;
  seller_id: number | null;
  status: string;
  total_amount: string;
  currency: string;
  items: OrderItem[];
};

export type InventoryItem = {
  id: number;
  inventory_kind?: "regular" | "fresh_produce";
  product_id: number;
  product_name?: string | null;
  product_type?: string | null;
  product_unit?: string | null;
  product_validity_days?: number | null;
  seller_id: number;
  supplier_id?: number | null;
  supplier_name?: string | null;
  supplier_email?: string | null;
  seller_email?: string | null;
  seller_status?: string | null;
  origin_type?: "seller_direct" | "procurement";
  origin?: "seller_direct" | "primary" | "secondary" | "reseller" | null;
  entry_date?: string | null;
  quantity: number;
  estimated_quantity?: number | null;
  stored_quantity?: number;
  is_expired?: boolean;
  updated_at?: string | null;
  created_by_admin_user_id: number;
};

export type Pagination = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type Product = {
  id: number;
  product_name: string;
  product_type: string;
  product_unit: string;
  validity_days: number;
};

export type ProductType = {
  id: number;
  product_type: string;
  product_count?: number;
};

export type Supplier = {
  supplier_id: number;
  supplier_name: string;
  email?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  address_line3?: string | null;
  phone_number?: string | null;
  is_active: boolean;
  product_links: Array<{
    product_id: number;
    supplier_type: "primary" | "secondary" | "reseller";
  }>;
  overall_rating?: number | null;
  rating_count?: number;
};

export type ProcurementOrder = {
  procurement_id: number;
  supplier_id: number;
  supplier_name?: string | null;
  product_id: number;
  product_name?: string | null;
  quantity: number;
  price_per_unit: string;
  total_value: string;
  procurement_date: string;
  status: "draft" | "placed" | "received" | "cancelled";
  pushed_to_inventory?: boolean;
  created_by_admin_user_id: number;
};

export type SupplierRating = {
  review_id: number;
  procurement_id: number;
  procurement_status?: string | null;
  supplier_id: number;
  supplier_name?: string | null;
  product_id: number;
  product_name?: string | null;
  rating: number;
  review_text?: string | null;
  reviewed_by_user_id: number;
  rated_by_email?: string | null;
  image_urls?: string[];
  image_paths?: string[];
  created_at: string;
};

export type Region = {
  region_id: number;
  region_name: string;
  region_description?: string | null;
  region_type: "source" | "distribution";
  distribution_level?: "major" | "minor" | "local" | null;
  parent_region_id?: number | null;
  parent_region_name?: string | null;
  default_admin_user_id?: number | null;
  default_ambassador_user_id?: number | null;
};

export type UserRow = {
  id: number;
  email: string;
  is_active: boolean;
  roles: string[];
  first_name?: string | null;
  last_name?: string | null;
  phone_number?: string | null;
  region?: string | null;
  major_distribution_region_id?: number | null;
  seller_status?: string | null;
  assigned_admin_user_id?: number | null;
};
