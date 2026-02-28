import { FormEvent, useEffect, useState } from "react";

import {
  createSupplierRating,
  listProcurementOrderOptions,
  listSupplierRatings
} from "../api/admin";
import { ApiError, API_BASE_URL } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { ProcurementOrder, SupplierRating } from "../types/models";

export function SupplierRatingsPage() {
  const { accessToken, hasRole } = useAuth();
  const [orders, setOrders] = useState<ProcurementOrder[]>([]);
  const [selectedProcurementId, setSelectedProcurementId] = useState("");
  const [reviews, setReviews] = useState<SupplierRating[]>([]);

  const [rating, setRating] = useState("1");
  const [reviewText, setReviewText] = useState("");
  const [images, setImages] = useState<File[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canManage = hasRole("admin") || hasRole("super_admin");

  const loadOrders = async () => {
    if (!accessToken || !canManage) return;
    try {
      const response = await listProcurementOrderOptions(accessToken, false);
      setOrders(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load procurement orders");
    }
  };

  const loadReviews = async (procurementId: number) => {
    if (!accessToken) return;
    try {
      const response = await listSupplierRatings(accessToken, procurementId);
      setReviews(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load reviews");
    }
  };

  useEffect(() => {
    loadOrders();
  }, [accessToken, canManage]);

  useEffect(() => {
    if (!selectedProcurementId) {
      setReviews([]);
      return;
    }
    loadReviews(Number(selectedProcurementId));
  }, [selectedProcurementId]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken || !selectedProcurementId) return;

    const ratingValue = Number(rating);
    if (!Number.isInteger(ratingValue) || ratingValue < 1 || ratingValue > 10) {
      setError("Rating must be integer between 1 and 10.");
      return;
    }

    try {
      await createSupplierRating(accessToken, Number(selectedProcurementId), {
        rating: ratingValue,
        review_text: reviewText || undefined,
        images
      });
      setMessage("Procurement review added.");
      setRating("1");
      setReviewText("");
      setImages([]);
      await loadReviews(Number(selectedProcurementId));
      await loadOrders();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add review");
    }
  };

  const imageUrl = (path: string) => {
    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }
    const base = API_BASE_URL.endsWith("/api/v1")
      ? API_BASE_URL.replace(/\/api\/v1$/, "")
      : "";
    return `${base}${path}`;
  };

  return (
    <AppShell>
      <h1>Supplier Reviews</h1>
      {!canManage ? (
        <p>Only Admin or Super Admin can manage supplier reviews.</p>
      ) : (
        <>
          <div style={{ display: "grid", gap: 8, maxWidth: 640, marginBottom: 14 }}>
            <label>
              Procurement Order
              <select
                value={selectedProcurementId}
                onChange={(e) => {
                  setSelectedProcurementId(e.target.value);
                  setMessage(null);
                }}
                style={{ display: "block", width: "100%" }}
              >
                <option value="">Select Non-Draft Procurement Order</option>
                {orders.map((o) => (
                  <option key={o.procurement_id} value={String(o.procurement_id)}>
                    #{o.procurement_id} | {o.supplier_name ?? o.supplier_id} | {o.product_name ?? o.product_id} | {o.status}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 640, marginBottom: 16 }}>
            <h3>Add Review (for selected order)</h3>
            <input placeholder="Rating (1-10)" value={rating} onChange={(e) => setRating(e.target.value)} />
            <textarea
              placeholder="Review text"
              rows={4}
              maxLength={3000}
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
            />
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) => setImages(Array.from(e.target.files ?? []))}
            />
            <button type="submit" disabled={!selectedProcurementId}>Submit Review</button>
          </form>

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <h3>Reviews</h3>
          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">Review ID</th>
                <th align="left">Order</th>
                <th align="left">Order Status</th>
                <th align="left">Supplier</th>
                <th align="left">Product</th>
                <th align="left">Rating</th>
                <th align="left">Text</th>
                <th align="left">Images</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((row) => (
                <tr key={row.review_id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{row.review_id}</td>
                  <td>{row.procurement_id}</td>
                  <td>{row.procurement_status ?? "-"}</td>
                  <td>{row.supplier_name ?? row.supplier_id}</td>
                  <td>{row.product_name ?? row.product_id}</td>
                  <td>{row.rating}</td>
                  <td>{row.review_text ?? "-"}</td>
                  <td>
                    {(row.image_urls ?? []).length === 0 ? (
                      "-"
                    ) : (
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {(row.image_urls ?? []).map((url, idx) => (
                          <a
                            key={`${row.review_id}-${idx}`}
                            href={imageUrl(url)}
                            target="_blank"
                            rel="noreferrer"
                            style={{ display: "inline-block" }}
                          >
                            <img
                              src={imageUrl(url)}
                              alt={`Review ${row.review_id} image ${idx + 1}`}
                              style={{
                                width: 64,
                                height: 64,
                                objectFit: "cover",
                                borderRadius: 6,
                                border: "1px solid #ddd"
                              }}
                            />
                          </a>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {reviews.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={8}>No reviews found for selected procurement order.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
