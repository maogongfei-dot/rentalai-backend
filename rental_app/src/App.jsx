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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <AIChatWidget />
    </>
  );
}

export default App;
