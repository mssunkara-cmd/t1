import { apiRequest } from "./client";
import type { Order, OrderItem } from "../types/models";

export function listOrders(token: string) {
  return apiRequest<{ items: Order[] }>("/orders", { method: "GET" }, token);
}

export function createOrder(
  token: string,
  payload: {
    seller_id: number;
    currency: string;
    items: Array<Pick<OrderItem, "sku" | "name" | "qty" | "unit_price">>;
  }
) {
  return apiRequest<{ id: number; order_number: string; status: string }>(
    "/orders",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
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
