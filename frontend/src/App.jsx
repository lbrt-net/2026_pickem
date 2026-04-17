import { BrowserRouter, Routes, Route } from "react-router-dom";
import PickemBoard from "./pages/PickemBoard";
import UserPicksPage from "./pages/UserPicksPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PickemBoard />} />
        <Route path="/user/:username" element={<UserPicksPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  );
}