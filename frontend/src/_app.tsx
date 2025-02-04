import { Route, Routes } from "react-router-dom";
import urls from "./urls";
import SessionPage from "./pages/session/details";
import DashboardPage from "./pages/dashboard";

function App() {
  return (
    <Routes>
      <Route path={urls.session.getHref()} element={<SessionPage />} />
      <Route path="/" element={<DashboardPage />} />
      <Route path={urls.dashboard.getHref()} element={<DashboardPage />} />
    </Routes>
  );
}

export default App;
