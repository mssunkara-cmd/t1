import { useEffect, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import { getOrderGroup } from "../api/orders";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { OrderGroup } from "../types/models";

export function OrderGroupDetailPage() {
  const { orderGroupId } = useParams();
  const { accessToken } = useAuth();
  const [group, setGroup] = useState<OrderGroup | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!accessToken || !orderGroupId) return;
      try {
        const data = await getOrderGroup(accessToken, Number(orderGroupId));
        setGroup(data);
        setError(null);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load order group");
      }
    };
    load();
  }, [accessToken, orderGroupId]);

  return (
    <AppShell>
      <h1>Order Group Detail</h1>
      <p><RouterLink to="/orders">Back to Orders</RouterLink></p>
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {!group ? (
        <p>Loading...</p>
      ) : (
        <>
          <p>Group: {group.group_number}</p>
          <p>Buyer: {group.buyer_name ?? group.buyer_email ?? group.buyer_id}</p>
          <p>Total: {group.total_amount} {group.currency}</p>
          <p>Created: {group.created_at ? new Date(group.created_at).toLocaleString() : "-"}</p>

          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Order #</th>
                <th align="left">Source</th>
                <th align="left">Status</th>
                <th align="left">Total</th>
                <th align="left">Items</th>
              </tr>
            </thead>
            <tbody>
              {group.orders.map((order) => (
                <tr key={order.id} style={{ borderTop: "1px solid #ddd", verticalAlign: "top" }}>
                  <td>{order.order_number}</td>
                  <td>{order.source_label ?? "-"}</td>
                  <td>{order.status}</td>
                  <td>{order.total_amount} {order.currency}</td>
                  <td>
                    <table cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
                      <thead>
                        <tr>
                          <th align="left">Product</th>
                          <th align="left">Qty</th>
                          <th align="left">Unit Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {order.items.map((item) => (
                          <tr key={item.id ?? `${order.id}-${item.sku}`} style={{ borderTop: "1px solid #eee" }}>
                            <td>{item.name}</td>
                            <td>{item.qty}</td>
                            <td>{item.unit_price}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
