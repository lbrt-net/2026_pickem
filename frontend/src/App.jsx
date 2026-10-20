import { Fragment, Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
const LandingPage = lazy(() => import("./pages/LandingPage"));
const Account = lazy(() => import("./pages/Account"));
const UnderConstruction = lazy(() => import("./pages/UnderConstruction"));
const Shooting = lazy(() => import("./pages/stats/Shooting"));
const Rebounding = lazy(() => import("./pages/stats/Rebounding"));
const Playmaking = lazy(() => import("./pages/stats/Playmaking"));
const StatsIndex = lazy(() => import("./pages/stats/StatsIndex"));
const ShotBreakdown = lazy(() => import("./pages/stats/ShotBreakdown"));
const Gravity = lazy(() => import("./pages/stats/Gravity"));
const CommunityBoard = lazy(() => import("./pages/CommunityBoard"));
const PickemBoard = lazy(() => import("./pages/PickemBoard"));
const UserPicksPage = lazy(() => import("./pages/UserPicksPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const LeaderboardPage = lazy(() => import("./pages/LeaderboardPage"));
const RulesPage = lazy(() => import("./pages/RulesPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const FantasyHome = lazy(() => import("./pages/fantasy/Home"));
const FantasyStandings = lazy(() => import("./pages/fantasy/Standings"));
const FantasyMatchup = lazy(() => import("./pages/fantasy/Matchup"));
const FantasyPlayers = lazy(() => import("./pages/fantasy/Players"));
import AutoRefresh from "./components/AutoRefresh";
const FantasyDraftRoom = lazy(() => import("./pages/fantasy/DraftRoom"));
const FantasyDraftRecap = lazy(() => import("./pages/fantasy/DraftRecap"));
const FantasyTrades = lazy(() => import("./pages/fantasy/Trades"));
const FantasyTransactions = lazy(() => import("./pages/fantasy/Transactions"));
const FantasyWinnings = lazy(() => import("./pages/fantasy/Winnings"));
const FantasyTeamManagement = lazy(() => import("./pages/fantasy/TeamManagement"));
const FantasyTeamSettings = lazy(() => import("./pages/fantasy/TeamSettings"));
const FantasyTenure = lazy(() => import("./pages/fantasy/Tenure"));
const FantasyPlayoffs = lazy(() => import("./pages/fantasy/Playoffs"));
const FantasyRecap = lazy(() => import("./pages/fantasy/Recap"));
const FantasyProjectionCheck = lazy(() => import("./pages/fantasy/ProjectionCheck"));
const FantasyPlayerPage = lazy(() => import("./pages/fantasy/player/PlayerPage"));
const FantasyScoring = lazy(() => import("./pages/fantasy/Scoring"));
const FantasyReplay = lazy(() => import("./pages/fantasy/Replay"));
const FantasyLeagueSettings = lazy(() => import("./pages/fantasy/LeagueSettings"));
const FantasyJoin = lazy(() => import("./pages/fantasy/Join"));
const SiteMap = lazy(() => import("./pages/SiteMap"));
const BagsLog = lazy(() => import("./pages/bags/BagsLog"));
const BagsLibrary = lazy(() => import("./pages/bags/BagsLibrary"));
import PageTitle from "./components/shared/PageTitle";
const NotThisRound = lazy(() => import("./pages/fantasy/NotThisRound"));
import { isOn } from "./components/fantasy/features";

// Every page loads on its own when it's visited (2026-10-18): one bundle used to carry every page — bags, stats,
// pickem and fantasy all downloaded and parsed together on any visit.

// Fantasy pages switched off for this testing round (features.js) render a placeholder.
const gate = (path, element) => (isOn(path) ? element : <NotThisRound />);

export default function App() {
  return (
    <BrowserRouter>
      <AutoRefresh />
      <PageTitle />
      <Suspense fallback={null}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/account" element={<Account />} />
        <Route path="/admin/sitemap" element={<SiteMap />} />
        {/* Hidden personal page: cornhole landing log, saved in the browser only. Not linked or in the site map. */}
        <Route path="/bags" element={<BagsLog />} />
        <Route path="/bags/library" element={<BagsLibrary />} />
        <Route path="/stats" element={<StatsIndex />} />
        <Route path="/stats/shooting" element={<Shooting />} />
        <Route path="/stats/rebounding" element={<Rebounding />} />
        <Route path="/stats/playmaking" element={<Playmaking />} />
        {/* Lineups and Defense are off the site (2026-10-19): Lineups until its numbers are fixed; Defense was the notes pass
            (the notes stay in nba_stats_notes and its code stays in pages/stats/) */}
        <Route path="/stats/gravity" element={<Gravity />} />
        <Route path="/stats/shooting/breakdown" element={<ShotBreakdown />} />

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
            <Route path={`${b}/players/:id`} element={<FantasyPlayerPage />} />
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
            <Route path={`${b}/projection-check`} element={gate("/projection-check", <FantasyProjectionCheck />)} />
            <Route path={`${b}/winnings`} element={<FantasyWinnings />} />
          </Fragment>
        ))}

        {/* Pure placeholder — proves the season selector works before a real 2027-28 fantasy exists. */}
        <Route path="/fantasy/2027_28/*" element={<UnderConstruction label="Fantasy 2027-28" />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
