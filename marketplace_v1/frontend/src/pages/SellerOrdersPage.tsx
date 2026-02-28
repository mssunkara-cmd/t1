import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { listOrders } from "../api/orders";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Order } from "../types/models";

export function SellerOrdersPage() {
  const { accessToken, hasRole } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!accessToken) return;
      try {
        const response = await listOrders(accessToken);
        setOrders(response.items);
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load seller orders");
      }
    };
    load();
  }, [accessToken]);

  return (
    <AppShell>
      <h1>Seller Orders</h1>
      {!hasRole("seller") ? (
        <p>Seller role is required.</p>
      ) : (
        <>
          {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Order #</th>
                <th align="left">Group</th>
                <th align="left">Buyer</th>
                <th align="left">Status</th>
                <th align="left">Total</th>
                <th align="left">Detail</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{order.order_number}</td>
                  <td>{order.group_number ?? "-"}</td>
                  <td>{order.buyer_id}</td>
                  <td>{order.status}</td>
                  <td>{order.total_amount} {order.currency}</td>
                  <td>
                    {order.order_group_id ? <RouterLink to={`/orders/groups/${order.order_group_id}`}>Open Group</RouterLink> : "-"}
                  </td>
                </tr>
              ))}
              {orders.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={6}>No seller orders found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
