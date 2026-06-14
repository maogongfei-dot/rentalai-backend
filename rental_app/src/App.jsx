import { Navigate, Route, Routes } from "react-router-dom";
import AIChatWidget from "./components/AIChatWidget";
import Navbar from "./components/Navbar.jsx";
import HomePage from "./pages/HomePage.jsx";
import GuideLibrary from "./pages/GuideLibrary.jsx";
import ShortRentPage from "./pages/ShortRentPage.jsx";
import CreateShortRentPage from "./pages/CreateShortRentPage.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Profile from "./pages/Profile.jsx";
import TenantDashboard from "./pages/TenantDashboard.jsx";
import LandlordDashboard from "./pages/LandlordDashboard.jsx";
import LandlordCenter from "./pages/LandlordCenter.jsx";
import ContractCenter from "./pages/ContractCenter.jsx";
import AreaCenter from "./pages/AreaCenter.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";

function App() {
  return (
    <>
      <Navbar />
      <main className="layout-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/guides" element={<GuideLibrary />} />
          <Route path="/short-rent" element={<ShortRentPage />} />
          <Route path="/create-short-rent" element={<CreateShortRentPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tenant-dashboard"
            element={
              <ProtectedRoute>
                <TenantDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/landlord-dashboard"
            element={
              <ProtectedRoute>
                <LandlordDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/landlord-center"
            element={
              <ProtectedRoute>
                <LandlordCenter />
              </ProtectedRoute>
            }
          />
          <Route
            path="/contract-center"
            element={
              <ProtectedRoute>
                <ContractCenter />
              </ProtectedRoute>
            }
          />
          <Route
            path="/area-center"
            element={
              <ProtectedRoute>
                <AreaCenter />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <AIChatWidget />
    </>
  );
}

export default App;
