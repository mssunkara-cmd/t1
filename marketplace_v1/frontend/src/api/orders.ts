import { apiRequest } from "./client";
import type { Order, OrderCatalogItem, OrderGroup, OrderItem } from "../types/models";

export function listOrders(token: string) {
  return apiRequest<{ items: Order[] }>("/orders", { method: "GET" }, token);
}

export function listOrderGroups(token: string) {
  return apiRequest<{ items: OrderGroup[] }>("/orders/groups", { method: "GET" }, token);
}

export function getOrderGroup(token: string, orderGroupId: number) {
  return apiRequest<OrderGroup>(`/orders/groups/${orderGroupId}`, { method: "GET" }, token);
}

export function createOrder(
  token: string,
  payload: {
    currency: string;
    items: Array<
      Pick<
        OrderItem,
        "sku" | "name" | "qty" | "unit_price" | "product_id" | "inventory_kind" | "source_inventory_item_id"
      > & { seller_id?: number | null; supplier_id?: number | null }
    >;
  }
) {
  return apiRequest<{ order_group_id: number; group_number: string; total_amount: string; currency: string; orders: Order[] }>(
    "/orders",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function searchOrderCatalog(
  token: string,
  filters?: { product_type?: string; product_name?: string; seller_name?: string; supplier_name?: string }
) {
  const params = new URLSearchParams();
  if (filters?.product_type) params.set("product_type", filters.product_type);
  if (filters?.product_name) params.set("product_name", filters.product_name);
  if (filters?.seller_name) params.set("seller_name", filters.seller_name);
  if (filters?.supplier_name) params.set("supplier_name", filters.supplier_name);
  const query = params.toString();
  const path = query ? `/orders/catalog?${query}` : "/orders/catalog";
  return apiRequest<{ items: OrderCatalogItem[] }>(path, { method: "GET" }, token);
}

export function listAmbassadorOrderGroups(token: string) {
  return apiRequest<{ items: OrderGroup[] }>("/orders/ambassador-groups", { method: "GET" }, token);
}

export function updateOrderStatus(token: string, orderId: number, status: string) {
  return apiRequest<{ id: number; status: string }>(
    `/orders/${orderId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status })
    },
    token
  );
}
