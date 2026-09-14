import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { createBackend } from "./backend";

const root = document.getElementById("root");
if (!root) throw new Error("Missing application root");

createRoot(root).render(
  <StrictMode>
    <App backend={createBackend()} />
  </StrictMode>,
);
