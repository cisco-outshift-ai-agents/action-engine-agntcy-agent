import React from "react";
import ReactDOM from "react-dom/client";
import App from "./_app";
import { BrowserRouter as Router } from "react-router-dom";
import { setTheme } from "@magnetic/theme";
import "./styles/global.css";

setTheme("dark-classic");
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Router>
      <App />
    </Router>
  </React.StrictMode>
);
