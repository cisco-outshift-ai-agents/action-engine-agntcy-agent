import React from "react";
import ReactDOM from "react-dom/client";
import App from "./_app";
import { BrowserRouter as Router } from "react-router-dom";
import { ThemeProvider } from "@/components/theme-provider";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Router>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </Router>
  </React.StrictMode>
);
