import { Routes, Route, Navigate } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import ClassroomsPage from "./pages/ClassroomsPage.jsx";
import ClassroomDetailPage from "./pages/ClassroomDetailPage.jsx";
import ClassroomStatsPage from "./pages/ClassroomStatsPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";
import HistoryDetailPage from "./pages/HistoryDetailPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";

export default function App() {
  return (
    <div className="app">
      <Nav />
      <main className="grow">
        <Routes>
          <Route path="/" element={<ClassroomsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/classroom/:id" element={<ClassroomDetailPage />} />
          <Route path="/classroom/:id/stats" element={<ClassroomStatsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:id" element={<HistoryDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="foot">
        <div className="container spread">
          <span>
            AI-cademics · a multi-agent classroom simulation
          </span>
          <span className="mono">teacher + 2 students · live sprints · auto-graded</span>
        </div>
      </footer>
    </div>
  );
}
