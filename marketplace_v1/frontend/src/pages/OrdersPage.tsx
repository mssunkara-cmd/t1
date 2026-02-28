import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { createOrder, listOrderGroups, listOrders, searchOrderCatalog, updateOrderStatus } from "../api/orders";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Order, OrderCatalogItem, OrderGroup } from "../types/models";

function SourceBadge({ sourceType }: { sourceType: "seller" | "supplier" }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        background: sourceType === "seller" ? "#d9f4ff" : "#e7f7df",
        color: sourceType === "seller" ? "#0b5a7a" : "#2f6b1f",
        marginRight: 8
      }}
    >
      {sourceType === "seller" ? "Seller" : "Supplier"}
    </span>
  );
}

type CartItem = {
  key: string;
  inventory_kind: "regular" | "fresh_produce";
  source_inventory_item_id: number;
  sourceType: "seller" | "supplier";
  seller_id?: number | null;
  supplier_id?: number | null;
  seller_name?: string | null;
  supplier_name?: string | null;
  product_id: number;
  product_name: string;
  product_type: string;
  product_unit?: string | null;
  source_label?: string | null;
  available_quantity: number;
  qty: string;
  unit_price: string;
  sku: string;
};

export function OrdersPage() {
  const { user, accessToken, hasRole } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [orderGroups, setOrderGroups] = useState<OrderGroup[]>([]);
  const [catalogItems, setCatalogItems] = useState<OrderCatalogItem[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);

  const [filterProductType, setFilterProductType] = useState("");
  const [filterProductName, setFilterProductName] = useState("");
  const [filterSellerName, setFilterSellerName] = useState("");
  const [filterSupplierName, setFilterSupplierName] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canUpdateStatus = hasRole("admin") || hasRole("super_admin") || hasRole("support_ops");
  const canSearchCatalog = hasRole("buyer") || canUpdateStatus;

  const loadOrders = async () => {
    if (!accessToken) return;
    try {
      const [ordersData, groupsData] = await Promise.all([
        listOrders(accessToken),
        listOrderGroups(accessToken)
      ]);
      setOrders(ordersData.items);
      setOrderGroups(groupsData.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load orders");
    }
  };

  const loadCatalog = async () => {
    if (!accessToken || !canSearchCatalog) return;
    try {
      const response = await searchOrderCatalog(accessToken, {
        product_type: filterProductType || undefined,
        product_name: filterProductName || undefined,
        seller_name: filterSellerName || undefined,
        supplier_name: filterSupplierName || undefined
      });
      setCatalogItems(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to search product catalog");
    }
  };

  useEffect(() => {
    loadOrders();
  }, [accessToken]);

  useEffect(() => {
    loadCatalog();
  }, [accessToken, canSearchCatalog, filterProductType, filterProductName, filterSellerName, filterSupplierName]);

  const cartSource = useMemo(() => {
    if (cart.length === 0) return [];
    return Array.from(new Set(cart.map((item) => item.source_label ?? "Unknown")));
  }, [cart]);

  const cartTotal = useMemo(
    () =>
      cart.reduce((sum, item) => {
        const qty = Number(item.qty);
        const unitPrice = Number(item.unit_price);
        if (!Number.isFinite(qty) || !Number.isFinite(unitPrice)) return sum;
        return sum + qty * unitPrice;
      }, 0),
    [cart]
  );

  const addToCart = (item: OrderCatalogItem) => {
    if (!item.can_order) {
      setError("This result cannot be ordered.");
      return;
    }

    const sourceType: "seller" | "supplier" = item.seller_id ? "seller" : "supplier";

    const key = `${sourceType}-${item.seller_id ?? "na"}-${item.supplier_id ?? "na"}-${item.product_id}`;
    setCart((prev) => {
      const existing = prev.find((row) => row.key === key);
      if (existing) {
        return prev.map((row) =>
          row.key === key
            ? {
                ...row,
                qty: String(Math.min(Number(row.qty || "0") + 1, item.available_quantity))
              }
            : row
        );
      }
      return [
        ...prev,
        {
          key,
          sourceType,
          inventory_kind: item.inventory_kind,
          source_inventory_item_id: item.inventory_item_id,
          seller_id: item.seller_id,
          supplier_id: item.supplier_id,
          seller_name: item.seller_name,
          supplier_name: item.supplier_name,
          product_id: item.product_id,
          product_name: item.product_name,
          product_type: item.product_type,
          product_unit: item.product_unit,
          source_label: item.source_label,
          available_quantity: item.available_quantity,
          qty: "1",
          unit_price: item.suggested_unit_price ?? "1.00",
          sku: `P-${item.product_id}`
        }
      ];
    });
    setMessage(`Added ${item.product_name} to cart.`);
    setError(null);
  };

  const updateCartItem = (key: string, patch: Partial<CartItem>) => {
    setCart((prev) => prev.map((item) => (item.key === key ? { ...item, ...patch } : item)));
  };

  const removeCartItem = (key: string) => {
    setCart((prev) => prev.filter((item) => item.key !== key));
  };

  const clearCart = () => setCart([]);

  const submitCart = async () => {
    if (!accessToken) return;
    if (cart.length === 0) {
      setError("Cart is empty.");
      return;
    }

    for (const item of cart) {
      const qty = Number(item.qty);
      const unitPrice = Number(item.unit_price);
      if (!Number.isInteger(qty) || qty <= 0) {
        setError(`Quantity must be a positive integer for ${item.product_name}.`);
        return;
      }
      if (qty > item.available_quantity) {
        setError(`Quantity exceeds available stock for ${item.product_name}.`);
        return;
      }
      if (!Number.isFinite(unitPrice) || unitPrice <= 0) {
        setError(`Unit price must be positive for ${item.product_name}.`);
        return;
      }
    }

    try {
      setError(null);
      const result = await createOrder(accessToken, {
        currency: "USD",
        items: cart.map((item) => ({
          seller_id: item.seller_id ?? undefined,
          supplier_id: item.supplier_id ?? undefined,
          sku: item.sku,
          name: item.product_name,
          product_id: item.product_id,
          inventory_kind: item.inventory_kind,
          source_inventory_item_id: item.source_inventory_item_id,
          qty: Number(item.qty),
          unit_price: item.unit_price
        }))
      });
      setMessage(`Checkout submitted: ${result.group_number}. Created ${result.orders.length} grouped orders.`);
      clearCart();
      await loadOrders();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Order submission failed");
    }
  };

  const setStatus = async (orderId: number, status: string) => {
    if (!accessToken) return;
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
          {canSearchCatalog ? (
            <>
              <h3>Search Products</h3>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
                <input placeholder="Product Type" value={filterProductType} onChange={(e) => setFilterProductType(e.target.value)} />
                <input placeholder="Product Name" value={filterProductName} onChange={(e) => setFilterProductName(e.target.value)} />
                <input placeholder="Seller Name" value={filterSellerName} onChange={(e) => setFilterSellerName(e.target.value)} />
                <input placeholder="Supplier Name" value={filterSupplierName} onChange={(e) => setFilterSupplierName(e.target.value)} />
              </div>

              <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginBottom: 20 }}>
                <thead>
                  <tr>
                    <th align="left">Product</th>
                    <th align="left">Type</th>
                    <th align="left">Source</th>
                    <th align="left">Available</th>
                    <th align="left">Suggested Price</th>
                    <th align="left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {catalogItems.map((item) => (
                    <tr key={`${item.inventory_kind}-${item.inventory_item_id}`} style={{ borderTop: "1px solid #ddd" }}>
                      <td>{item.product_name}{item.product_unit ? ` (${item.product_unit})` : ""}</td>
                      <td>{item.product_type}</td>
                      <td><SourceBadge sourceType={item.seller_id ? "seller" : "supplier"} />{item.source_label ?? "-"}</td>
                      <td>{item.available_quantity}</td>
                      <td>{item.suggested_unit_price ?? "-"}</td>
                      <td>
                        <button type="button" onClick={() => addToCart(item)} disabled={!item.can_order}>
                          {item.can_order ? "Add to Cart" : "Not Orderable"}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {catalogItems.length === 0 ? (
                    <tr style={{ borderTop: "1px solid #ddd" }}>
                      <td colSpan={6}>No matching products found.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>

              <h3>Cart Review</h3>
              {cartSource.length > 0 ? (
                <p>
                  Sources: {cartSource.join(", ")}
                </p>
              ) : null}
              <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginBottom: 16 }}>
                <thead>
                  <tr>
                    <th align="left">Product</th>
                    <th align="left">Source</th>
                    <th align="left">Type</th>
                    <th align="left">Available</th>
                    <th align="left">Qty</th>
                    <th align="left">Unit Price</th>
                    <th align="left">Line Total</th>
                    <th align="left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {cart.map((item) => (
                    <tr key={item.key} style={{ borderTop: "1px solid #ddd" }}>
                      <td>{item.product_name}</td>
                      <td><SourceBadge sourceType={item.sourceType} />{item.source_label ?? "-"}</td>
                      <td>{item.product_type}</td>
                      <td>{item.available_quantity}</td>
                      <td>
                        <input
                          value={item.qty}
                          onChange={(e) => updateCartItem(item.key, { qty: e.target.value })}
                          style={{ width: 80 }}
                        />
                      </td>
                      <td>
                        <input
                          value={item.unit_price}
                          onChange={(e) => updateCartItem(item.key, { unit_price: e.target.value })}
                          style={{ width: 100 }}
                        />
                      </td>
                      <td>{(Number(item.qty || "0") * Number(item.unit_price || "0")).toFixed(2)}</td>
                      <td>
                        <button type="button" onClick={() => removeCartItem(item.key)}>Remove</button>
                      </td>
                    </tr>
                  ))}
                  {cart.length === 0 ? (
                    <tr style={{ borderTop: "1px solid #ddd" }}>
                      <td colSpan={8}>Cart is empty.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>

              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 20 }}>
                <strong>Total: {cartTotal.toFixed(2)} USD</strong>
                <button type="button" onClick={submitCart} disabled={cart.length === 0}>
                  Submit Order
                </button>
                <button type="button" onClick={clearCart} disabled={cart.length === 0}>
                  Clear Cart
                </button>
              </div>
            </>
          ) : null}

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <h3>Checkout Groups</h3>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%", marginBottom: 24 }}>
            <thead>
              <tr>
                <th align="left">Group</th>
                <th align="left">Created</th>
                <th align="left">Total</th>
                <th align="left">Orders</th>
                <th align="left">Detail</th>
              </tr>
            </thead>
            <tbody>
              {orderGroups.map((group) => (
                <tr key={group.order_group_id} style={{ borderTop: "1px solid #ddd", verticalAlign: "top" }}>
                  <td>{group.group_number}</td>
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
                        </tr>
                      </thead>
                      <tbody>
                        {group.orders.map((order) => (
                          <tr key={order.id} style={{ borderTop: "1px solid #eee" }}>
                            <td>{order.order_number}</td>
                            <td>{order.source_label ?? "-"}</td>
                            <td>{order.status}</td>
                            <td>{order.total_amount} {order.currency}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </td>
                  <td><RouterLink to={`/orders/groups/${group.order_group_id}`}>Open Group</RouterLink></td>
                </tr>
              ))}
              {orderGroups.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={5}>No checkout groups found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>

          <h3>Order List</h3>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Order #</th>
                <th align="left">Group</th>
                <th align="left">Buyer</th>
                <th align="left">Source</th>
                <th align="left">Status</th>
                <th align="left">Total</th>
                <th align="left">Action</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{order.order_number}</td>
                  <td>{order.group_number ?? "-"}</td>
                  <td>{order.buyer_id}</td>
                  <td>{order.source_label ?? order.seller_name ?? order.supplier_name ?? order.seller_id ?? order.supplier_id ?? "-"}</td>
                  <td>{order.status}</td>
                  <td>{order.total_amount} {order.currency}</td>
                  <td>
                    {canUpdateStatus ? (
                      <select defaultValue={order.status} onChange={(e) => setStatus(order.id, e.target.value)}>
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
