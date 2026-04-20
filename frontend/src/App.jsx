import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import CommunityBoard from "./pages/CommunityBoard";
import PickemBoard from "./pages/PickemBoard";
import UserPicksPage from "./pages/UserPicksPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Main page: community aggregate view */}
        <Route path="/" element={<CommunityBoard />} />

        {/* /picks/me → PickemBoard handles resolving to logged-in user */}
        <Route path="/picks/me" element={<PickemBoard />} />

        {/* /picks/:username → own picks (editable) or someone else's (readonly after lock) */}
        <Route path="/picks/:username" element={<PickemBoard />} />

        {/* Legacy /user/:username redirect */}
        <Route path="/user/:username" element={<UserPicksPage />} />

        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  );
}