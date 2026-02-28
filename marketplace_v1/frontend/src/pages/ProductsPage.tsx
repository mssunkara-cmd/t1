import { FormEvent, useEffect, useState } from "react";

import {
  createProduct,
  createProductType,
  deleteProduct,
  deleteProductType,
  listProducts,
  listProductTypes,
  updateProduct
} from "../api/admin";
import { ApiError } from "../api/client";
import { useAuth } from "../app/auth";
import { AppShell } from "../components/layout/AppShell";
import type { Product, ProductType } from "../types/models";

export function ProductsPage() {
  const { accessToken, hasRole } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [productTypes, setProductTypes] = useState<ProductType[]>([]);
  const [productName, setProductName] = useState("");
  const [productType, setProductType] = useState("");
  const [newProductType, setNewProductType] = useState("");
  const [productUnit, setProductUnit] = useState("");
  const [validityDays, setValidityDays] = useState("365");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const canManage = hasRole("admin") || hasRole("super_admin");

  const load = async () => {
    if (!accessToken || !canManage) {
      return;
    }
    try {
      const [productsResponse, productTypesResponse] = await Promise.all([
        listProducts(accessToken),
        listProductTypes(accessToken)
      ]);
      setProducts(productsResponse.items);
      setProductTypes(productTypesResponse.items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load products");
    }
  };

  useEffect(() => {
    load();
  }, [accessToken, canManage]);

  const resetForm = () => {
    setEditingId(null);
    setProductName("");
    setProductType("");
    setProductUnit("");
    setValidityDays("365");
  };

  const validate = () => {
    if (!productName.trim() || !productType.trim() || !productUnit.trim()) {
      return "All fields are required.";
    }
    if (productName.length > 100) {
      return "Product Name max length is 100.";
    }
    if (productUnit.length > 10) {
      return "Product Unit max length is 10.";
    }
    const days = Number(validityDays);
    if (!Number.isInteger(days) || days < 1 || days > 36500) {
      return "Validity Days must be an integer between 1 and 36500.";
    }
    return null;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!accessToken) {
      return;
    }

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setError(null);
      const days = Number(validityDays);
      if (editingId) {
        await updateProduct(accessToken, editingId, {
          product_name: productName,
          product_type: productType,
          product_unit: productUnit,
          validity_days: days
        });
        setMessage("Product updated.");
      } else {
        await createProduct(accessToken, {
          product_name: productName,
          product_type: productType,
          product_unit: productUnit,
          validity_days: days
        });
        setMessage("Product created.");
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save product");
    }
  };

  const startEdit = (product: Product) => {
    setEditingId(product.id);
    setProductName(product.product_name);
    setProductType(product.product_type);
    setProductUnit(product.product_unit);
    setValidityDays(String(product.validity_days));
  };

  const remove = async (id: number) => {
    if (!accessToken) {
      return;
    }
    try {
      await deleteProduct(accessToken, id);
      setMessage("Product deleted.");
      if (editingId === id) {
        resetForm();
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete product");
    }
  };

  const addType = async () => {
    if (!accessToken) return;
    const value = newProductType.trim();
    if (!value) {
      setError("Product Type is required.");
      return;
    }
    if (value.length > 50) {
      setError("Product Type max length is 50.");
      return;
    }

    try {
      setError(null);
      await createProductType(accessToken, { product_type: value });
      setMessage("Product type created.");
      setNewProductType("");
      const productTypesResponse = await listProductTypes(accessToken);
      setProductTypes(productTypesResponse.items);
      if (!productType) {
        setProductType(value);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create product type");
    }
  };

  const removeType = async (type: ProductType) => {
    if (!accessToken) return;
    if ((type.product_count ?? 0) > 0) {
      setError("Cannot delete product type with associated products.");
      return;
    }
    try {
      setError(null);
      await deleteProductType(accessToken, type.id);
      setMessage("Product type deleted.");
      if (productType === type.product_type) {
        setProductType("");
      }
      const productTypesResponse = await listProductTypes(accessToken);
      setProductTypes(productTypesResponse.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete product type");
    }
  };

  const productTypeOptions =
    productTypes.some((row) => row.product_type === productType) || !productType
      ? productTypes
      : [{ id: -1, product_type: productType }, ...productTypes];

  return (
    <AppShell>
      <h1>Products</h1>
      {!canManage ? (
        <p>Only Admin or Super Admin can manage products.</p>
      ) : (
        <>
          <form onSubmit={submit} style={{ display: "grid", gap: 8, maxWidth: 520, marginBottom: 18 }}>
            <input
              placeholder="Product Name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              maxLength={100}
            />
            <div style={{ display: "grid", gap: 6 }}>
              <select value={productType} onChange={(e) => setProductType(e.target.value)}>
                <option value="">Select Product Type</option>
                {productTypeOptions.map((row) => (
                  <option key={row.id} value={row.product_type}>
                    {row.product_type}
                  </option>
                ))}
              </select>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  placeholder="Add New Product Type"
                  value={newProductType}
                  onChange={(e) => setNewProductType(e.target.value)}
                  maxLength={50}
                />
                <button type="button" onClick={addType}>
                  Add Type
                </button>
              </div>
              <table cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
                <thead>
                  <tr>
                    <th align="left">Type</th>
                    <th align="left">Products</th>
                    <th align="left">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {productTypes.map((row) => (
                    <tr key={row.id} style={{ borderTop: "1px solid #eee" }}>
                      <td>{row.product_type}</td>
                      <td>{row.product_count ?? 0}</td>
                      <td>
                        <button type="button" onClick={() => removeType(row)} disabled={(row.product_count ?? 0) > 0}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                  {productTypes.length === 0 ? (
                    <tr style={{ borderTop: "1px solid #eee" }}>
                      <td colSpan={3}>No product types found.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <input
              placeholder="Product Unit"
              value={productUnit}
              onChange={(e) => setProductUnit(e.target.value)}
              maxLength={10}
            />
            <input
              placeholder="Validity Days"
              value={validityDays}
              onChange={(e) => setValidityDays(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit">{editingId ? "Update Product" : "Create Product"}</button>
              {editingId ? (
                <button type="button" onClick={resetForm}>
                  Cancel Edit
                </button>
              ) : null}
            </div>
          </form>

          {message && <p style={{ color: "green" }}>{message}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}

          <table cellPadding={8} style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th align="left">ID</th>
                <th align="left">Name</th>
                <th align="left">Type</th>
                <th align="left">Unit</th>
                <th align="left">Validity (days)</th>
                <th align="left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id} style={{ borderTop: "1px solid #ddd" }}>
                  <td>{product.id}</td>
                  <td>{product.product_name}</td>
                  <td>{product.product_type}</td>
                  <td>{product.product_unit}</td>
                  <td>{product.validity_days}</td>
                  <td style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => startEdit(product)}>Edit</button>
                    <button onClick={() => remove(product.id)}>Delete</button>
                  </td>
                </tr>
              ))}
              {products.length === 0 ? (
                <tr style={{ borderTop: "1px solid #ddd" }}>
                  <td colSpan={6}>No products found.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </>
      )}
    </AppShell>
  );
}
