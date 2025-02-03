import { Route, Routes } from "react-router-dom";
import urls from "./urls";
import SessionPage from "./pages/session";

function App() {
  return (
    <Routes>
      <Route path={urls.session.getHref()} element={<SessionPage />} />
    </Routes>
  );
}

export default App;
