import { Navigate, Route, Routes } from "react-router-dom";
import AIChatWidget from "./components/AIChatWidget";
import Navbar from "./components/Navbar.jsx";
import HomePage from "./pages/HomePage.jsx";
import ShortRentPage from "./pages/ShortRentPage.jsx";
import CreateShortRentPage from "./pages/CreateShortRentPage.jsx";

function App() {
  return (
    <>
      <Navbar />
      <main className="layout-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/short-rent" element={<ShortRentPage />} />
          <Route path="/create-short-rent" element={<CreateShortRentPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <AIChatWidget />
    </>
  );
}

export default App;
