import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import CommunityBoard from "./pages/CommunityBoard";
import PickemBoard from "./pages/PickemBoard";
import UserPicksPage from "./pages/UserPicksPage";
import AdminPage from "./pages/AdminPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import RulesPage from "./pages/RulesPage";
import UsersPage from "./pages/UsersPage";
import FantasyHome from "./pages/fantasy/Home";
import FantasyStandings from "./pages/fantasy/Standings";
import FantasyMatchup from "./pages/fantasy/Matchup";
import FantasyPlayers from "./pages/fantasy/Players";
import FantasyDraftRoom from "./pages/fantasy/DraftRoom";
import FantasyDraftRecap from "./pages/fantasy/DraftRecap";
import FantasyTrades from "./pages/fantasy/Trades";
import FantasyTransactions from "./pages/fantasy/Transactions";
import FantasyTeamManagement from "./pages/fantasy/TeamManagement";
import FantasyTeamSettings from "./pages/fantasy/TeamSettings";
import FantasyTenure from "./pages/fantasy/Tenure";
import FantasyPlayoffs from "./pages/fantasy/Playoffs";
import FantasyRecap from "./pages/fantasy/Recap";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />

        {/* "Pickem" always opens the latest year with no year-select step. */}
        <Route path="/pickem" element={<Navigate to="/pickem/2026" replace />} />

        <Route path="/pickem/2026" element={<CommunityBoard />} />
        <Route path="/pickem/2026/picks/me" element={<PickemBoard />} />
        <Route path="/pickem/2026/picks/:username" element={<PickemBoard />} />
        <Route path="/pickem/2026/user/:username" element={<UserPicksPage />} />
        <Route path="/pickem/2026/admin" element={<AdminPage />} />
        <Route path="/pickem/2026/users" element={<UsersPage />} />
        <Route path="/pickem/2026/leaderboard" element={<LeaderboardPage />} />
        <Route path="/pickem/2026/rules" element={<RulesPage />} />

        {/* "Fantasy" always opens the latest season with no season-select step. */}
        <Route path="/fantasy" element={<Navigate to="/fantasy/2026-27" replace />} />

        <Route path="/fantasy/2026-27" element={<FantasyHome />} />
        <Route path="/fantasy/2026-27/standings" element={<FantasyStandings />} />
        <Route path="/fantasy/2026-27/matchup" element={<FantasyMatchup />} />
        <Route path="/fantasy/2026-27/players" element={<FantasyPlayers />} />
        <Route path="/fantasy/2026-27/draft" element={<FantasyDraftRoom />} />
        <Route path="/fantasy/2026-27/draft/recap" element={<FantasyDraftRecap />} />
        <Route path="/fantasy/2026-27/trades" element={<FantasyTrades />} />
        <Route path="/fantasy/2026-27/transactions" element={<FantasyTransactions />} />
        <Route path="/fantasy/2026-27/team" element={<FantasyTeamManagement />} />
        <Route path="/fantasy/2026-27/team/settings" element={<FantasyTeamSettings />} />
        <Route path="/fantasy/2026-27/tenure" element={<FantasyTenure />} />
        <Route path="/fantasy/2026-27/playoffs" element={<FantasyPlayoffs />} />
        <Route path="/fantasy/2026-27/recap" element={<FantasyRecap />} />
      </Routes>
    </BrowserRouter>
  );
}
