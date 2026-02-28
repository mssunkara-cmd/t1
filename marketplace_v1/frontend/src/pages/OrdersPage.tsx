import { FormEvent, useEffect, useState } from "react";

import { createOrder, listOrders, updateOrderStatus } from "../api/orders";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Order } from "../types/models";

export function OrdersPage() {
  const { user, accessToken, hasRole } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [sellerId, setSellerId] = useState("0");
  const [sku, setSku] = useState("");
  const [name, setName] = useState("");
  const [qty, setQty] = useState("1");
  const [unitPrice, setUnitPrice] = useState("0.00");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canUpdateStatus = hasRole("admin") || hasRole("super_admin") || hasRole("support_ops");

  const loadOrders = async () => {
    if (!accessToken) {
      return;
    }
    try {
      const data = await listOrders(accessToken);
      setOrders(data.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load orders");
    }
  };

  useEffect(() => {
    loadOrders();
  }, [accessToken]);

  const submitOrder = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken) {
      return;
    }

    try {
      setError(null);
      const result = await createOrder(accessToken, {
        seller_id: Number(sellerId),
        currency: "USD",
        items: [
          {
            sku,
            name,
            qty: Number(qty),
            unit_price: unitPrice
          }
        ]
      });
      setMessage(`Order created: ${result.order_number}`);
      setSku("");
      setName("");
      setQty("1");
      setUnitPrice("0.00");
      await loadOrders();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Order creation failed");
    }
  };

  const setStatus = async (orderId: number, status: string) => {
    if (!accessToken) {
      return;
    }
    try {
      await updateOrderStatus(accessToken, orderId, status);
      await loadOrders();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update order status");
    }
  };

  return (
    <AppShell>
      <h1>Orders</h1>
      {!user || !accessToken ? (
        <p>Please login first.</p>
      ) : (
        <>
          <form onSubmit={submitOrder} style={{ display: "grid", gap: 8, maxWidth: 520, marginBottom: 20 }}>
            <h3>Place New Order</h3>
            <input
              placeholder="Seller User ID"
              value={sellerId}
              onChange={(e) => setSellerId(e.target.value)}
            />
            <input placeholder="Item SKU" value={sku} onChange={(e) => setSku(e.target.value)} />
            <input placeholder="Item Name" value={name} onChange={(e) => setName(e.target.value)} />
            <input placeholder="Quantity" value={qty} onChange={(e) => setQty(e.target.value)} />
            <input
              placeholder="Unit Price"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
            />
            <button type="submit">Create Order</button>
          </form>

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <h3>Order List</h3>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Order #</th>
                <th align="left">Buyer</th>
                <th align="left">Seller</th>
                <th align="left">Status</th>
                <th align="left">Total</th>
                <th align="left">Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{order.order_number}</td>
                  <td>{order.buyer_id}</td>
                  <td>{order.seller_id}</td>
                  <td>{order.status}</td>
                  <td>{order.total_amount} {order.currency}</td>
                  <td>
                    {canUpdateStatus ? (
                      <select
                        defaultValue={order.status}
                        onChange={(e) => setStatus(order.id, e.target.value)}
                      >
                        <option value="created">created</option>
                        <option value="confirmed">confirmed</option>
                        <option value="packed">packed</option>
                        <option value="shipped">shipped</option>
                        <option value="delivered">delivered</option>
                        <option value="cancelled">cancelled</option>
                      </select>
                    ) : (
                      "-"
                    )}
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
