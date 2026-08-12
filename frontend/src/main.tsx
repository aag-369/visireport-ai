import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";
import { tokenStorage } from "./api/client";
import { useAuthStore } from "./store/uiStore";

// Rehydrate the auth store from localStorage on load (real JWT persistence
// across reloads, not just component state).
const existingToken = tokenStorage.get("visireport_token");
if (existingToken) {
  try {
    const payload = JSON.parse(atob(existingToken.split(".")[1]));
    useAuthStore.getState().setAuth(existingToken, payload.name ?? "Engineer", payload.role ?? "engineer");
  } catch {
    tokenStorage.clear("visireport_token");
  }
}

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
