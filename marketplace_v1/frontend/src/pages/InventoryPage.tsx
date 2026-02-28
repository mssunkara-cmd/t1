import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createInventoryItem,
  deleteInventoryItem,
  listInventory,
  listInventoryProductOptions,
  listInventorySellerOptions,
  updateInventoryItem
} from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { InventoryItem, Pagination, Product, UserRow } from "../types/models";

type InventoryStatusFilter = "" | "pending_validation" | "valid" | "rejected" | "active" | "inactive";

export function InventoryPage() {
  const { accessToken, hasRole } = useAuth();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [sellers, setSellers] = useState<UserRow[]>([]);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [selectedSellerId, setSelectedSellerId] = useState("");
  const [quantity, setQuantity] = useState("0");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingKind, setEditingKind] = useState<"regular" | "fresh_produce">("regular");

  const [filterProductId, setFilterProductId] = useState("");
  const [filterProductType, setFilterProductType] = useState("");
  const [filterSellerId, setFilterSellerId] = useState("");
  const [filterStatus, setFilterStatus] = useState<InventoryStatusFilter>("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [pagination, setPagination] = useState<Pagination>({ page: 1, page_size: 10, total: 0, total_pages: 0 });

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const isAdminLike = hasRole("admin") || hasRole("super_admin");
  const isSellerOnly = hasRole("seller") && !isAdminLike;

  const load = async () => {
    if (!accessToken || (!isAdminLike && !isSellerOnly)) {
      return;
    }

    try {
      const inventoryResponse = await listInventory(accessToken, {
        page,
        page_size: pageSize,
        seller_id: filterSellerId ? Number(filterSellerId) : undefined,
        product_id: filterProductId ? Number(filterProductId) : undefined,
        product_type: filterProductType || undefined,
        status: filterStatus || undefined
      });
      setItems(inventoryResponse.items);
      setPagination(inventoryResponse.pagination);

      const productsResponse = await listInventoryProductOptions(accessToken);
      setProducts(productsResponse.items);

      if (isAdminLike) {
        const sellersResponse = await listInventorySellerOptions(accessToken);
        setSellers(sellersResponse.items);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load inventory");
    }
  };

  useEffect(() => {
    load();
  }, [accessToken, isAdminLike, isSellerOnly, page, pageSize, filterProductId, filterProductType, filterSellerId, filterStatus]);

  const productTypeOptions = useMemo(
    () => Array.from(new Set(products.map((p) => p.product_type).filter((p): p is string => Boolean(p)))).sort(),
    [products]
  );

  const resetForm = () => {
    setEditingId(null);
    setEditingKind("regular");
    setSelectedProductId("");
    setSelectedSellerId("");
    setQuantity("0");
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken || !isAdminLike) {
      if (!accessToken || !isSellerOnly) {
        return;
      }
    }

    const qty = Number(quantity);
    if (isAdminLike) {
      if (!selectedProductId || !selectedSellerId || !Number.isInteger(qty) || qty < 0) {
        setError("Select product, seller and provide non-negative integer quantity.");
        return;
      }
    } else if (isSellerOnly) {
      if (!selectedProductId || !Number.isInteger(qty) || qty < 0) {
        setError("Select product and provide non-negative integer quantity.");
        return;
      }
    }

    try {
      setError(null);
      if (editingId) {
        await updateInventoryItem(accessToken, editingId, qty, editingKind);
        setMessage("Inventory item updated.");
      } else {
        await createInventoryItem(accessToken, {
          product_id: Number(selectedProductId),
          ...(isAdminLike ? { seller_id: Number(selectedSellerId) } : {}),
          quantity: qty
        });
        setMessage("Inventory item created.");
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save inventory item");
    }
  };

  const startEdit = (item: InventoryItem) => {
    setEditingId(item.id);
    setEditingKind(item.inventory_kind ?? "regular");
    setSelectedProductId(String(item.product_id));
    setSelectedSellerId(String(item.seller_id));
    setQuantity(String(item.stored_quantity ?? item.estimated_quantity ?? item.quantity));
  };

  const remove = async (itemId: number, inventoryKind?: "regular" | "fresh_produce") => {
    if (!accessToken || (!isAdminLike && !isSellerOnly)) {
      return;
    }
    try {
      await deleteInventoryItem(accessToken, itemId, inventoryKind);
      setMessage("Inventory item deleted.");
      if (editingId === itemId) {
        resetForm();
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete inventory item");
    }
  };

  const title = useMemo(() => {
    if (isAdminLike) {
      return "Inventory (Admin Scope)";
    }
    if (isSellerOnly) {
      return "My Inventory";
    }
    return "Inventory";
  }, [isAdminLike, isSellerOnly]);

  return (
    <AppShell>
      <h1>{title}</h1>
      {!isAdminLike && !isSellerOnly ? (
        <p>Admin/Super Admin or Seller role is required.</p>
      ) : (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            <select value={filterProductId} onChange={(e) => { setFilterProductId(e.target.value); setPage(1); }}>
              <option value="">All Products</option>
              {products.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.product_name}
                </option>
              ))}
            </select>
            <select value={filterProductType} onChange={(e) => { setFilterProductType(e.target.value); setPage(1); }}>
              <option value="">All Product Types</option>
              {productTypeOptions.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            {isAdminLike ? (
              <select value={filterSellerId} onChange={(e) => { setFilterSellerId(e.target.value); setPage(1); }}>
                <option value="">All Sellers</option>
                {sellers.map((s) => (
                  <option key={s.id} value={String(s.id)}>
                    {s.email}
                  </option>
                ))}
              </select>
            ) : null}
            <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value as InventoryStatusFilter); setPage(1); }}>
              <option value="">All Status</option>
              <option value="pending_validation">pending_validation</option>
              <option value="valid">valid</option>
              <option value="rejected">rejected</option>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
            <select value={String(pageSize)} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              <option value="10">10 / page</option>
              <option value="20">20 / page</option>
              <option value="50">50 / page</option>
            </select>
          </div>

          {(isAdminLike || isSellerOnly) ? (
            <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 520, marginBottom: 20 }}>
              <h3>{editingId ? "Edit Inventory Item" : isSellerOnly ? "Add My Inventory" : "Create Inventory Item"}</h3>
              <select value={selectedProductId} onChange={(e) => setSelectedProductId(e.target.value)}>
                <option value="">Select Product</option>
                {products.map((p) => (
                  <option key={p.id} value={String(p.id)}>
                    {p.product_name} ({p.product_type}/{p.product_unit}, {p.validity_days}d)
                  </option>
                ))}
              </select>
              {isAdminLike ? (
                <select value={selectedSellerId} onChange={(e) => setSelectedSellerId(e.target.value)}>
                  <option value="">Select Seller</option>
                  {sellers.map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.id} - {s.email}
                    </option>
                  ))}
                </select>
              ) : null}
              <input
                placeholder="Quantity"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit">{editingId ? "Update" : "Create"}</button>
                  {editingId ? (
                    <button type="button" onClick={resetForm}>
                      Cancel
                    </button>
                  ) : null}
              </div>
            </form>
          ) : null}

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">ID</th>
                <th align="left">Product</th>
                <th align="left">Source</th>
                <th align="left">Source Status</th>
                <th align="left">Origin</th>
                <th align="left">Entry Date</th>
                <th align="left">Quantity</th>
                <th align="left">Stored Qty</th>
                <th align="left">Expiry</th>
                {isAdminLike ? <th align="left">Created By Admin</th> : null}
                {(isAdminLike || isSellerOnly) ? <th align="left">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={`${item.inventory_kind ?? "regular"}-${item.id}`} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{item.id}</td>
                  <td>
                    {item.product_name ?? "-"}
                    {item.product_type || item.product_unit
                      ? ` (${item.product_type ?? ""}/${item.product_unit ?? ""})`
                      : ""}
                  </td>
                  <td>{item.origin_type === "procurement" ? (item.supplier_name ?? item.supplier_id ?? "-") : (item.seller_email ?? item.seller_id ?? "-")}</td>
                  <td>{item.seller_status ?? "-"}</td>
                  <td>{item.origin ?? "-"}</td>
                  <td>{item.entry_date ? new Date(item.entry_date).toLocaleString() : "-"}</td>
                  <td>{item.quantity}</td>
                  <td>
                    {item.inventory_kind === "fresh_produce"
                      ? (item.estimated_quantity ?? item.stored_quantity ?? item.quantity)
                      : (item.stored_quantity ?? item.quantity)}
                  </td>
                  <td>{item.is_expired ? "Expired (0 available)" : "Active"}</td>
                  {isAdminLike ? <td>{item.created_by_admin_user_id}</td> : null}
                  {(isAdminLike || isSellerOnly) ? (
                    <td style={{ display: "flex", gap: 8 }}>
                      <button onClick={() => startEdit(item)}>Edit Qty</button>
                      <button onClick={() => remove(item.id, item.inventory_kind ?? "regular")}>Delete</button>
                    </td>
                  ) : null}
                </tr>
              ))}
              {items.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={isAdminLike ? 11 : 10}>No inventory items found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>

          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={pagination.page <= 1}>
              Previous
            </button>
            <span>
              Page {pagination.page} / {Math.max(1, pagination.total_pages)} (Total {pagination.total})
            </span>
            <button
              onClick={() => setPage((p) => (pagination.total_pages ? Math.min(p + 1, pagination.total_pages) : p + 1))}
              disabled={pagination.total_pages > 0 ? pagination.page >= pagination.total_pages : true}
            >
              Next
            </button>
          </div>
        </>
      )}
    </AppShell>
  );
}
