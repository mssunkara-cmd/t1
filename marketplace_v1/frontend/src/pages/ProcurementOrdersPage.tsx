import { FormEvent, Fragment, useEffect, useState } from "react";

import {
  createSupplierRating,
  createProcurementOrder,
  listProcurementOrders,
  listProducts,
  listSupplierRatings,
  listSupplierOptions,
  pushProcurementOrderToInventory,
  updateProcurementOrderStatus
} from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Pagination, ProcurementOrder, Product, SupplierRating } from "../types/models";

type ProcurementStatus = "draft" | "placed" | "received" | "cancelled";

function parseReviewHistory(text: string | null | undefined): Array<{ timestamp: string | null; body: string }> {
  if (!text) return [];
  const normalized = text.trim();
  if (!normalized) return [];

  const parts = normalized.split(/\n\s*\n(?=\[)/g);
  return parts.map((part) => {
    const match = part.match(/^\[(.+?)\]\s*([\s\S]*)$/);
    if (match) {
      return {
        timestamp: match[1]?.trim() || null,
        body: (match[2] ?? "").trim()
      };
    }
    return { timestamp: null, body: part.trim() };
  });
}

export function ProcurementOrdersPage() {
  const { accessToken, hasRole } = useAuth();
  const [orders, setOrders] = useState<ProcurementOrder[]>([]);
  const [suppliers, setSuppliers] = useState<
    Array<{ supplier_id: number; supplier_name: string; email?: string | null }>
  >([]);
  const [products, setProducts] = useState<Product[]>([]);

  const [supplierId, setSupplierId] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("0");
  const [pricePerUnit, setPricePerUnit] = useState("0.00");
  const [procurementDate, setProcurementDate] = useState("");
  const [status, setStatus] = useState<ProcurementStatus>("draft");

  const [filterSupplierId, setFilterSupplierId] = useState("");
  const [filterProductId, setFilterProductId] = useState("");
  const [filterStatus, setFilterStatus] = useState<"" | ProcurementStatus>("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [pagination, setPagination] = useState<Pagination>({ page: 1, page_size: 10, total: 0, total_pages: 0 });
  const [reviewOpenOrderId, setReviewOpenOrderId] = useState<number | null>(null);
  const [reviewItemsByOrder, setReviewItemsByOrder] = useState<Record<number, SupplierRating[]>>({});
  const [reviewRating, setReviewRating] = useState("1");
  const [reviewText, setReviewText] = useState("");
  const [reviewImages, setReviewImages] = useState<File[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canManage = hasRole("admin") || hasRole("super_admin");

  const load = async () => {
    if (!accessToken || !canManage) return;
    try {
      const [ordersResponse, supplierResponse, productsResponse] = await Promise.all([
        listProcurementOrders(accessToken, {
          page,
          page_size: pageSize,
          supplier_id: filterSupplierId ? Number(filterSupplierId) : undefined,
          product_id: filterProductId ? Number(filterProductId) : undefined,
          status: filterStatus || undefined
        }),
        listSupplierOptions(accessToken),
        listProducts(accessToken)
      ]);
      setOrders(ordersResponse.items);
      setPagination(ordersResponse.pagination);
      setSuppliers(supplierResponse.items);
      setProducts(productsResponse.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load procurement data");
    }
  };

  useEffect(() => {
    load();
  }, [accessToken, canManage, page, pageSize, filterSupplierId, filterProductId, filterStatus]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken) return;

    const qty = Number(quantity);
    if (!supplierId || !productId || !Number.isInteger(qty) || qty < 0) {
      setError("Select supplier/product and provide non-negative integer quantity.");
      return;
    }

    try {
      await createProcurementOrder(accessToken, {
        supplier_id: Number(supplierId),
        product_id: Number(productId),
        quantity: qty,
        price_per_unit: pricePerUnit,
        procurement_date: procurementDate || undefined,
        status
      });
      setMessage("Procurement order created.");
      setSupplierId("");
      setProductId("");
      setQuantity("0");
      setPricePerUnit("0.00");
      setProcurementDate("");
      setStatus("draft");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create procurement order");
    }
  };

  const changeStatus = async (procurementId: number, nextStatus: ProcurementStatus) => {
    if (!accessToken) return;
    try {
      await updateProcurementOrderStatus(accessToken, procurementId, nextStatus);
      setMessage(`Procurement order ${procurementId} updated to ${nextStatus}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update status");
    }
  };

  const pushToInventory = async (procurementId: number) => {
    if (!accessToken) return;
    try {
      await pushProcurementOrderToInventory(accessToken, procurementId);
      setMessage(`Procurement order ${procurementId} moved to inventory.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to push procurement to inventory");
    }
  };

  const loadReviews = async (procurementId: number) => {
    if (!accessToken) return;
    try {
      const response = await listSupplierRatings(accessToken, procurementId);
      setReviewItemsByOrder((prev) => ({ ...prev, [procurementId]: response.items }));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load reviews");
    }
  };

  const toggleReviewPanel = async (order: ProcurementOrder) => {
    if (reviewOpenOrderId === order.procurement_id) {
      setReviewOpenOrderId(null);
      return;
    }
    setReviewOpenOrderId(order.procurement_id);
    setReviewRating("1");
    setReviewText("");
    setReviewImages([]);
    await loadReviews(order.procurement_id);
  };

  const submitReview = async (order: ProcurementOrder) => {
    if (!accessToken) return;
    const rating = Number(reviewRating);
    if (!Number.isInteger(rating) || rating < 1 || rating > 10) {
      setError("Review rating must be integer between 1 and 10.");
      return;
    }
    try {
      await createSupplierRating(accessToken, order.procurement_id, {
        rating,
        review_text: reviewText || undefined,
        images: reviewImages
      });
      setMessage(`Review added for procurement order ${order.procurement_id}.`);
      setReviewRating("1");
      setReviewText("");
      setReviewImages([]);
      await loadReviews(order.procurement_id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add review");
    }
  };

  return (
    <AppShell>
      <h1>Procurement Orders</h1>
      {!canManage ? (
        <p>Only Admin or Super Admin can manage procurement orders.</p>
      ) : (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            <select value={filterSupplierId} onChange={(e) => { setFilterSupplierId(e.target.value); setPage(1); }}>
              <option value="">All Suppliers</option>
              {suppliers.map((s) => (
                <option key={s.supplier_id} value={String(s.supplier_id)}>
                  {s.supplier_name}
                </option>
              ))}
            </select>
            <select value={filterProductId} onChange={(e) => { setFilterProductId(e.target.value); setPage(1); }}>
              <option value="">All Products</option>
              {products.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.product_name}
                </option>
              ))}
            </select>
            <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value as "" | ProcurementStatus); setPage(1); }}>
              <option value="">All Status</option>
              <option value="draft">draft</option>
              <option value="placed">placed</option>
              <option value="received">received</option>
              <option value="cancelled">cancelled</option>
            </select>
          </div>

          <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 520, marginBottom: 16 }}>
            <h3>Create Procurement Order</h3>
            <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
              <option value="">Select Supplier</option>
              {suppliers.map((s) => (
                <option key={s.supplier_id} value={String(s.supplier_id)}>
                  {s.supplier_name}
                </option>
              ))}
            </select>
            <select value={productId} onChange={(e) => setProductId(e.target.value)}>
              <option value="">Select Product</option>
              {products.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.product_name}
                </option>
              ))}
            </select>
            <input placeholder="Quantity" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
            <input placeholder="Price Per Unit" value={pricePerUnit} onChange={(e) => setPricePerUnit(e.target.value)} />
            <input
              type="datetime-local"
              value={procurementDate}
              onChange={(e) => setProcurementDate(e.target.value)}
            />
            <select value={status} onChange={(e) => setStatus(e.target.value as ProcurementStatus)}>
              <option value="draft">draft</option>
              <option value="placed">placed</option>
              <option value="received">received</option>
              <option value="cancelled">cancelled</option>
            </select>
            <button type="submit">Create</button>
          </form>

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">ID</th>
                <th align="left">Supplier</th>
                <th align="left">Product</th>
                <th align="left">Qty</th>
                <th align="left">Price/Unit</th>
                <th align="left">Total</th>
                <th align="left">Date</th>
                <th align="left">Status</th>
                <th align="left">Inventory Push</th>
                <th align="left">Review</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <Fragment key={order.procurement_id}>
                  <tr style={{ borderTop: "1px solid #ddd" }}>
                    <td>{order.procurement_id}</td>
                    <td>{order.supplier_name ?? order.supplier_id}</td>
                    <td>{order.product_name ?? order.product_id}</td>
                    <td>{order.quantity}</td>
                    <td>{order.price_per_unit}</td>
                    <td>{order.total_value}</td>
                    <td>{new Date(order.procurement_date).toLocaleString()}</td>
                    <td>
                      <select
                        value={order.status}
                        onChange={(e) => changeStatus(order.procurement_id, e.target.value as ProcurementStatus)}
                        disabled={Boolean(order.pushed_to_inventory)}
                      >
                        <option value="draft">draft</option>
                        <option value="placed">placed</option>
                        <option value="received">received</option>
                        <option value="cancelled">cancelled</option>
                      </select>
                    </td>
                    <td>
                      {order.status === "received" ? (
                        <button
                          onClick={() => pushToInventory(order.procurement_id)}
                          disabled={Boolean(order.pushed_to_inventory)}
                        >
                          {order.pushed_to_inventory ? "Pushed" : "Push to Inventory"}
                        </button>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td>
                      {order.status === "draft" ? (
                        "-"
                      ) : (
                        <button onClick={() => toggleReviewPanel(order)}>
                          {reviewOpenOrderId === order.procurement_id ? "Hide Review" : "Review"}
                        </button>
                      )}
                    </td>
                  </tr>
                  {reviewOpenOrderId === order.procurement_id ? (
                    <tr style={{ borderTop: "1px solid #eee", background: "#fafafa" }}>
                      <td colSpan={10}>
                        <div style={{ display: "grid", gap: 8, maxWidth: 680 }}>
                          <strong>Order Review</strong>
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <input
                              placeholder="Rating (1-10)"
                              value={reviewRating}
                              onChange={(e) => setReviewRating(e.target.value)}
                            />
                            <input
                              placeholder="Review text"
                              value={reviewText}
                              onChange={(e) => setReviewText(e.target.value)}
                              style={{ minWidth: 320 }}
                            />
                            <input
                              type="file"
                              accept="image/*"
                              multiple
                              onChange={(e) => setReviewImages(Array.from(e.target.files ?? []))}
                            />
                            <button onClick={() => submitReview(order)}>
                              {(reviewItemsByOrder[order.procurement_id] ?? []).length > 0
                                ? "Update Review"
                                : "Submit Review"}
                            </button>
                          </div>
                          <div>
                            {(reviewItemsByOrder[order.procurement_id] ?? []).length === 0 ? (
                              <span>No reviews yet.</span>
                            ) : (
                              (reviewItemsByOrder[order.procurement_id] ?? []).map((review) => (
                                <div key={review.review_id} style={{ marginBottom: 10 }}>
                                  <div>
                                    Rating: {review.rating} | Status: {review.procurement_status ?? order.status} | By:{" "}
                                    {review.rated_by_email ?? review.reviewed_by_user_id}
                                  </div>
                                  <div style={{ marginTop: 6, display: "grid", gap: 6 }}>
                                    {parseReviewHistory(review.review_text).length === 0 ? (
                                      <span>-</span>
                                    ) : (
                                      parseReviewHistory(review.review_text).map((entry, idx) => (
                                        <div
                                          key={`${review.review_id}-entry-${idx}`}
                                          style={{
                                            border: "1px solid #e5e7eb",
                                            borderRadius: 6,
                                            padding: 8,
                                            background: "#fff"
                                          }}
                                        >
                                          {entry.timestamp ? (
                                            <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>
                                              {entry.timestamp}
                                            </div>
                                          ) : null}
                                          <div>{entry.body || "-"}</div>
                                        </div>
                                      ))
                                    )}
                                  </div>
                                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
                                    {(review.image_urls ?? []).map((url, idx) => (
                                      <a key={`${review.review_id}-${idx}`} href={url} target="_blank" rel="noreferrer">
                                        <img
                                          src={url}
                                          alt={`Review ${review.review_id} image ${idx + 1}`}
                                          style={{
                                            width: 56,
                                            height: 56,
                                            objectFit: "cover",
                                            borderRadius: 6,
                                            border: "1px solid #ddd"
                                          }}
                                        />
                                      </a>
                                    ))}
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
              {orders.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={10}>No procurement orders found.</td>
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
              onClick={() =>
                setPage((p) => (pagination.total_pages ? Math.min(p + 1, pagination.total_pages) : p + 1))
              }
              disabled={pagination.total_pages > 0 ? pagination.page >= pagination.total_pages : true}
            >
              Next
            </button>
            <select value={String(pageSize)} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              <option value="10">10 / page</option>
              <option value="20">20 / page</option>
              <option value="50">50 / page</option>
            </select>
          </div>
        </>
      )}
    </AppShell>
  );
}
