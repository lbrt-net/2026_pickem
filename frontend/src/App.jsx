import { BrowserRouter, Routes, Route } from "react-router-dom";
import CommunityBoard from "./pages/CommunityBoard";
import PickemBoard from "./pages/PickemBoard";
import UserPicksPage from "./pages/UserPicksPage";
import AdminPage from "./pages/AdminPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import RulesPage from "./pages/RulesPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CommunityBoard />} />
        <Route path="/picks/me" element={<PickemBoard />} />
        <Route path="/picks/:username" element={<PickemBoard />} />
        <Route path="/user/:username" element={<UserPicksPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/rules" element={<RulesPage />} />
      </Routes>
    </BrowserRouter>
  );
}
