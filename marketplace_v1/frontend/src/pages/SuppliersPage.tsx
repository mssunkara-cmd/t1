import { FormEvent, Fragment, useEffect, useMemo, useState } from "react";

import {
  createSupplier,
  deleteSupplier,
  getSupplierDetail,
  listProducts,
  listSuppliers,
  updateSupplier
} from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Product, Supplier } from "../types/models";

type LinkRow = { product_id: string; supplier_type: "primary" | "secondary" | "reseller" };

export function SuppliersPage() {
  const { accessToken, hasRole } = useAuth();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);

  const [supplierName, setSupplierName] = useState("");
  const [email, setEmail] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [addressLine3, setAddressLine3] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [productLinks, setProductLinks] = useState<LinkRow[]>([{ product_id: "", supplier_type: "primary" }]);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [expandedSupplierId, setExpandedSupplierId] = useState<number | null>(null);
  const [supplierDetail, setSupplierDetail] = useState<{
    supplier_id: number;
    rating_breakdown: Array<{ rating: number; orders: number }>;
    reviews: Array<{
      review_id: number;
      procurement_id: number;
      procurement_status?: string | null;
      rating: number;
      review_text?: string | null;
      created_at?: string | null;
    }>;
    overall_rating?: number | null;
    rating_count?: number;
  } | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canManage = hasRole("admin") || hasRole("super_admin");

  const productNameById = useMemo(
    () => new Map<number, string>(products.map((p) => [p.id, p.product_name])),
    [products]
  );

  const load = async () => {
    if (!accessToken || !canManage) return;
    try {
      const [suppliersResponse, productsResponse] = await Promise.all([
        listSuppliers(accessToken),
        listProducts(accessToken)
      ]);
      setSuppliers(suppliersResponse.items);
      setProducts(productsResponse.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load suppliers");
    }
  };

  useEffect(() => {
    load();
  }, [accessToken, canManage]);

  const resetForm = () => {
    setEditingId(null);
    setSupplierName("");
    setEmail("");
    setAddressLine1("");
    setAddressLine2("");
    setAddressLine3("");
    setPhoneNumber("");
    setIsActive(true);
    setProductLinks([{ product_id: "", supplier_type: "primary" }]);
  };

  const validate = () => {
    if (!supplierName.trim()) return "Supplier Name is required.";
    if (supplierName.length > 250) return "Supplier Name max length is 250.";
    if (email.length > 255) return "Email max length is 255.";
    if (addressLine1.length > 100 || addressLine2.length > 100 || addressLine3.length > 100) {
      return "Address lines max length is 100 each.";
    }
    if (phoneNumber.length > 12) return "Phone Number max length is 12.";
    if (productLinks.length === 0) return "Add at least one product link.";
    for (const row of productLinks) {
      if (!row.product_id) return "Each product link must have a product selected.";
    }
    return null;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken) return;

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    const payload = {
      supplier_name: supplierName,
      email: email || undefined,
      address_line1: addressLine1 || undefined,
      address_line2: addressLine2 || undefined,
      address_line3: addressLine3 || undefined,
      phone_number: phoneNumber || undefined,
      is_active: isActive,
      product_links: productLinks.map((row) => ({
        product_id: Number(row.product_id),
        supplier_type: row.supplier_type
      }))
    };

    try {
      setError(null);
      if (editingId) {
        await updateSupplier(accessToken, editingId, payload);
        setMessage("Supplier updated.");
      } else {
        await createSupplier(accessToken, payload);
        setMessage("Supplier created.");
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save supplier");
    }
  };

  const startEdit = (supplier: Supplier) => {
    setEditingId(supplier.supplier_id);
    setSupplierName(supplier.supplier_name);
    setEmail(supplier.email ?? "");
    setAddressLine1(supplier.address_line1 ?? "");
    setAddressLine2(supplier.address_line2 ?? "");
    setAddressLine3(supplier.address_line3 ?? "");
    setPhoneNumber(supplier.phone_number ?? "");
    setIsActive(supplier.is_active);
    setProductLinks(
      supplier.product_links.length
        ? supplier.product_links.map((link) => ({
            product_id: String(link.product_id),
            supplier_type: link.supplier_type
          }))
        : [{ product_id: "", supplier_type: "primary" }]
    );
  };

  const remove = async (supplierId: number) => {
    if (!accessToken) return;
    try {
      await deleteSupplier(accessToken, supplierId);
      setMessage("Supplier deleted.");
      if (editingId === supplierId) resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete supplier");
    }
  };

  const toggleDetail = async (supplierId: number) => {
    if (!accessToken) return;
    if (expandedSupplierId === supplierId) {
      setExpandedSupplierId(null);
      setSupplierDetail(null);
      return;
    }
    try {
      const detail = await getSupplierDetail(accessToken, supplierId);
      setExpandedSupplierId(supplierId);
      setSupplierDetail({
        supplier_id: detail.supplier_id,
        rating_breakdown: detail.rating_breakdown,
        reviews: detail.reviews ?? [],
        overall_rating: detail.overall_rating,
        rating_count: detail.rating_count
      });
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load supplier detail");
    }
  };

  const updateLinkRow = (index: number, patch: Partial<LinkRow>) => {
    setProductLinks((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  const addLinkRow = () => setProductLinks((prev) => [...prev, { product_id: "", supplier_type: "primary" }]);
  const removeLinkRow = (index: number) =>
    setProductLinks((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev));

  return (
    <AppShell>
      <h1>Suppliers</h1>
      {!canManage ? (
        <p>Only Admin or Super Admin can manage suppliers.</p>
      ) : (
        <>
          <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 720, marginBottom: 16 }}>
            <input placeholder="Supplier Name" value={supplierName} onChange={(e) => setSupplierName(e.target.value)} />
            <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <input placeholder="Address Line 1" value={addressLine1} onChange={(e) => setAddressLine1(e.target.value)} />
            <input placeholder="Address Line 2" value={addressLine2} onChange={(e) => setAddressLine2(e.target.value)} />
            <input placeholder="Address Line 3" value={addressLine3} onChange={(e) => setAddressLine3(e.target.value)} />
            <input placeholder="Phone Number" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} />
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Active
            </label>

            <div style={{ display: "grid", gap: 8 }}>
              <strong>Supplied Products</strong>
              {productLinks.map((row, index) => (
                <div key={index} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <select value={row.product_id} onChange={(e) => updateLinkRow(index, { product_id: e.target.value })}>
                    <option value="">Select Product</option>
                    {products.map((product) => (
                      <option key={product.id} value={String(product.id)}>
                        {product.product_name}
                      </option>
                    ))}
                  </select>
                  <select
                    value={row.supplier_type}
                    onChange={(e) =>
                      updateLinkRow(index, {
                        supplier_type: e.target.value as "primary" | "secondary" | "reseller"
                      })
                    }
                  >
                    <option value="primary">primary</option>
                    <option value="secondary">secondary</option>
                    <option value="reseller">reseller</option>
                  </select>
                  <button type="button" onClick={() => removeLinkRow(index)} disabled={productLinks.length <= 1}>
                    Remove
                  </button>
                </div>
              ))}
              <button type="button" onClick={addLinkRow}>Add Product Link</button>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit">{editingId ? "Update Supplier" : "Create Supplier"}</button>
              {editingId ? (
                <button type="button" onClick={resetForm}>Cancel Edit</button>
              ) : null}
            </div>
          </form>

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">ID</th>
                <th align="left">Supplier</th>
                <th align="left">Email</th>
                <th align="left">Phone</th>
                <th align="left">Active</th>
                <th align="left">Overall Rating</th>
                <th align="left">Products</th>
                <th align="left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => (
                <Fragment key={supplier.supplier_id}>
                  <tr style={{ borderTop: "1px solid #ddd" }}>
                    <td>{supplier.supplier_id}</td>
                    <td>{supplier.supplier_name}</td>
                    <td>{supplier.email ?? "-"}</td>
                    <td>{supplier.phone_number ?? "-"}</td>
                    <td>{supplier.is_active ? "yes" : "no"}</td>
                    <td>
                      {supplier.overall_rating != null
                        ? `${supplier.overall_rating} (${supplier.rating_count ?? 0})`
                        : "-"}
                    </td>
                    <td>
                      {supplier.product_links
                        .map((link) => `${productNameById.get(link.product_id) ?? link.product_id}:${link.supplier_type}`)
                        .join(", ") || "-"}
                    </td>
                    <td style={{ display: "flex", gap: 8 }}>
                      <button onClick={() => startEdit(supplier)}>Edit</button>
                      <button onClick={() => remove(supplier.supplier_id)}>Delete</button>
                      <button onClick={() => toggleDetail(supplier.supplier_id)}>
                        {expandedSupplierId === supplier.supplier_id ? "Hide Details" : "View Details"}
                      </button>
                    </td>
                  </tr>
                  {expandedSupplierId === supplier.supplier_id && supplierDetail ? (
                    <tr style={{ borderTop: "1px solid #eee", background: "#fafafa" }}>
                            <td colSpan={8}>
                              <strong>Supplier Rating Details</strong>
                              <div style={{ marginTop: 8, marginBottom: 10 }}>
                                {supplierDetail.rating_breakdown.length === 0 ? (
                                  <span>No reviewed orders yet.</span>
                                ) : (
                                  <table
                                    cellPadding={6}
                                    style={{ borderCollapse: "collapse", width: "100%", marginBottom: 10 }}
                                  >
                                    <thead>
                                      <tr>
                                        <th align="left">Rating</th>
                                        <th align="left">Orders</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {supplierDetail.rating_breakdown.map((row) => (
                                        <tr key={row.rating} style={{ borderTop: "1px solid #eee" }}>
                                          <td>{row.rating}</td>
                                          <td>{row.orders}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                )}
                              </div>
                              <strong>Reviews</strong>
                              <div style={{ marginTop: 8 }}>
                                {supplierDetail.reviews.length === 0 ? (
                                  <span>No review text available.</span>
                                ) : (
                                  <table cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
                                    <thead>
                                      <tr>
                                        <th align="left">Rating</th>
                                        <th align="left">Order</th>
                                        <th align="left">Status</th>
                                        <th align="left">Review Text</th>
                                        <th align="left">Date</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {supplierDetail.reviews.map((review) => (
                                        <tr key={review.review_id} style={{ borderTop: "1px solid #eee" }}>
                                          <td>{review.rating}</td>
                                          <td>{review.procurement_id}</td>
                                          <td>{review.procurement_status ?? "-"}</td>
                                          <td style={{ whiteSpace: "pre-wrap" }}>{review.review_text ?? "-"}</td>
                                          <td>
                                            {review.created_at ? new Date(review.created_at).toLocaleString() : "-"}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                )}
                              </div>
                            </td>
                          </tr>
                        ) : null}
                </Fragment>
              ))}
              {suppliers.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={8}>No suppliers found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
