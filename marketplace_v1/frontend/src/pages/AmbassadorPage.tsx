import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { listAmbassadorBuyers } from "../api/admin";
import { listAmbassadorOrderGroups } from "../api/orders";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { OrderGroup, UserRow } from "../types/models";

export function AmbassadorPage() {
  const { user, accessToken, hasRole } = useAuth();
  const [buyers, setBuyers] = useState<UserRow[]>([]);
  const [orderGroups, setOrderGroups] = useState<OrderGroup[]>([]);
  const [error, setError] = useState<string | null>(null);

  const buyersById = useMemo(() => new Map(buyers.map((buyer) => [buyer.id, buyer])), [buyers]);

  const load = async () => {
    if (!user || !accessToken) {
      return;
    }
    try {
      const [buyerData, orderData] = await Promise.all([
        listAmbassadorBuyers(accessToken, user.id),
        listAmbassadorOrderGroups(accessToken)
      ]);
      setBuyers(buyerData.items);
      setOrderGroups(orderData.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load ambassador data");
    }
  };

  useEffect(() => {
    if (hasRole("ambassador")) {
      load();
    }
  }, [user?.id, accessToken]);

  return (
    <AppShell>
      <h1>Ambassador Buyer Group</h1>
      {!hasRole("ambassador") ? (
        <p>Ambassador role is required.</p>
      ) : (
        <>
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <h3>Assigned Buyers</h3>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginBottom: 24 }}>
            <thead>
              <tr>
                <th align="left">Buyer ID</th>
                <th align="left">Email</th>
                <th align="left">Name</th>
                <th align="left">Phone</th>
                <th align="left">Region</th>
              </tr>
            </thead>
            <tbody>
              {buyers.map((buyer) => (
                <tr key={buyer.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{buyer.id}</td>
                  <td>{buyer.email}</td>
                  <td>{[buyer.first_name, buyer.last_name].filter(Boolean).join(" ") || "-"}</td>
                  <td>{buyer.phone_number ?? "-"}</td>
                  <td>{buyer.region ?? "-"}</td>
                </tr>
              ))}
              {buyers.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={5}>No buyers assigned.</td>
                </tr>
              ) : null}
            </tbody>
          </table>

          <h3>My Buyers Orders</h3>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Checkout Group</th>
                <th align="left">Buyer</th>
                <th align="left">Created</th>
                <th align="left">Total</th>
                <th align="left">Grouped Orders</th>
                <th align="left">Detail</th>
              </tr>
            </thead>
            <tbody>
              {orderGroups.map((group) => {
                const buyer = buyersById.get(group.buyer_id);
                return (
                  <tr key={group.order_group_id} style={{ borderTop: "1px solid #ddd", verticalAlign: "top" }}>
                    <td>{group.group_number}</td>
                    <td>{group.buyer_name ?? buyer?.email ?? group.buyer_email ?? group.buyer_id}</td>
                    <td>{group.created_at ? new Date(group.created_at).toLocaleString() : "-"}</td>
                    <td>{group.total_amount} {group.currency}</td>
                    <td>
                      <table cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
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
                            <tr key={order.id} style={{ borderTop: "1px solid #eee" }}>
                              <td>{order.order_number}</td>
                              <td>{order.source_label ?? "-"}</td>
                              <td>{order.status}</td>
                              <td>{order.total_amount} {order.currency}</td>
                              <td>
                                <table cellPadding={4} style={{ borderCollapse: "collapse", width: "100%" }}>
                                  <thead>
                                    <tr>
                                      <th align="left">Product</th>
                                      <th align="left">Qty</th>
                                      <th align="left">Unit Price</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {order.items.map((item) => (
                                      <tr key={item.id ?? `${order.id}-${item.sku}`} style={{ borderTop: "1px solid #f0f0f0" }}>
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
                    </td>
                    <td><RouterLink to={`/orders/groups/${group.order_group_id}`}>Open Group</RouterLink></td>
                  </tr>
                );
              })}
              {orderGroups.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={6}>No buyer order groups found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
