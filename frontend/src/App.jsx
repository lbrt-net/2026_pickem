import { Fragment } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import Account from "./pages/Account";
import UnderConstruction from "./pages/UnderConstruction";
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
import AutoRefresh from "./components/AutoRefresh";
import FantasyDraftRoom from "./pages/fantasy/DraftRoom";
import FantasyDraftRecap from "./pages/fantasy/DraftRecap";
import FantasyTrades from "./pages/fantasy/Trades";
import FantasyTransactions from "./pages/fantasy/Transactions";
import FantasyTeamManagement from "./pages/fantasy/TeamManagement";
import FantasyTeamSettings from "./pages/fantasy/TeamSettings";
import FantasyTenure from "./pages/fantasy/Tenure";
import FantasyPlayoffs from "./pages/fantasy/Playoffs";
import FantasyRecap from "./pages/fantasy/Recap";
import FantasyPlayerDetail from "./pages/fantasy/PlayerDetail";
import FantasyScoring from "./pages/fantasy/Scoring";
import FantasyReplay from "./pages/fantasy/Replay";
import FantasyLeagueSettings from "./pages/fantasy/LeagueSettings";
import FantasyJoin from "./pages/fantasy/Join";
import SiteMap from "./pages/SiteMap";
import PageTitle from "./components/shared/PageTitle";
import NotThisRound from "./pages/fantasy/NotThisRound";
import { isOn } from "./components/fantasy/features";

// Fantasy pages switched off for this testing round (features.js) render a placeholder.
const gate = (path, element) => (isOn(path) ? element : <NotThisRound />);

export default function App() {
  return (
    <BrowserRouter>
      <AutoRefresh />
      <PageTitle />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/account" element={<Account />} />
        <Route path="/admin/sitemap" element={<SiteMap />} />

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

        {/* Pure placeholder — proves the year selector works before a real 2027 pickem exists. */}
        <Route path="/pickem/2027/*" element={<UnderConstruction label="Pickem 2027" />} />

        {/* "Fantasy" always opens the latest season with no season-select step. */}
        <Route path="/fantasy" element={<Navigate to="/fantasy/2026_27" replace />} />

        {/* 2026-27, and the 2025-26 test league on the same pages (the URL picks the league). */}
        {["/fantasy/2026_27", "/fantasy/2025_26"].map(b => (
          <Fragment key={b}>
            <Route path={b} element={<FantasyHome />} />
            <Route path={`${b}/standings`} element={<FantasyStandings />} />
            <Route path={`${b}/matchup`} element={<FantasyMatchup />} />
            <Route path={`${b}/scoring`} element={<FantasyScoring />} />
            <Route path={`${b}/replay`} element={<FantasyReplay />} />
            <Route path={`${b}/league-settings`} element={<FantasyLeagueSettings />} />
            <Route path={`${b}/join`} element={<FantasyJoin />} />
            <Route path={`${b}/league`} element={<Navigate to={`${b}/join`} replace />} />
            <Route path={`${b}/players`} element={<FantasyPlayers />} />
            <Route path={`${b}/players/:id`} element={<FantasyPlayerDetail />} />
            <Route path={`${b}/draft`} element={<FantasyDraftRoom />} />
            <Route path={`${b}/draft/room`} element={<FantasyDraftRoom page="room" />} />
            <Route path={`${b}/draft/results`} element={<FantasyDraftRoom page="results" />} />
            <Route path={`${b}/draft/recap`} element={gate("/draft/recap", <FantasyDraftRecap />)} />
            <Route path={`${b}/trades`} element={gate("/trades", <FantasyTrades />)} />
            <Route path={`${b}/transactions`} element={gate("/transactions", <FantasyTransactions />)} />
            <Route path={`${b}/team`} element={<FantasyTeamManagement />} />
            <Route path={`${b}/team/settings`} element={gate("/team/settings", <FantasyTeamSettings />)} />
            <Route path={`${b}/team/:ownerId`} element={<FantasyTeamManagement />} />
            <Route path={`${b}/tenure`} element={gate("/tenure", <FantasyTenure />)} />
            <Route path={`${b}/playoffs`} element={<FantasyPlayoffs />} />
            <Route path={`${b}/recap`} element={gate("/recap", <FantasyRecap />)} />
          </Fragment>
        ))}

        {/* Pure placeholder — proves the season selector works before a real 2027-28 fantasy exists. */}
        <Route path="/fantasy/2027_28/*" element={<UnderConstruction label="Fantasy 2027-28" />} />
      </Routes>
    </BrowserRouter>
  );
}
