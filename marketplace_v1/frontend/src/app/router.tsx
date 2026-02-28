import { createBrowserRouter } from "react-router-dom";

import { DashboardPage } from "../pages/DashboardPage";
import { AmbassadorPage } from "../pages/AmbassadorPage";
import { BuyerGroupsPage } from "../pages/BuyerGroupsPage";
import { InventoryPage } from "../pages/InventoryPage";
import { LoginPage } from "../pages/LoginPage";
import { OrdersPage } from "../pages/OrdersPage";
import { OrderGroupDetailPage } from "../pages/OrderGroupDetailPage";
import { ProfilePage } from "../pages/ProfilePage";
import { ProcurementOrdersPage } from "../pages/ProcurementOrdersPage";
import { ProductsPage } from "../pages/ProductsPage";
import { RegionsPage } from "../pages/RegionsPage";
import { RegisterPage } from "../pages/RegisterPage";
import { SellerValidationPage } from "../pages/SellerValidationPage";
import { SellerOrdersPage } from "../pages/SellerOrdersPage";
import { SuppliersPage } from "../pages/SuppliersPage";
import { SuperAdminPage } from "../pages/SuperAdminPage";

export const router = createBrowserRouter([
  { path: "/", element: <DashboardPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  { path: "/profile", element: <ProfilePage /> },
  { path: "/orders", element: <OrdersPage /> },
  { path: "/orders/groups/:orderGroupId", element: <OrderGroupDetailPage /> },
  { path: "/seller-orders", element: <SellerOrdersPage /> },
  { path: "/products", element: <ProductsPage /> },
  { path: "/suppliers", element: <SuppliersPage /> },
  { path: "/procurement-orders", element: <ProcurementOrdersPage /> },
  { path: "/regions", element: <RegionsPage /> },
  { path: "/ambassador", element: <AmbassadorPage /> },
  { path: "/buyer-groups", element: <BuyerGroupsPage /> },
  { path: "/seller-validation", element: <SellerValidationPage /> },
  { path: "/inventory", element: <InventoryPage /> },
  { path: "/super-admin", element: <SuperAdminPage /> }
]);
