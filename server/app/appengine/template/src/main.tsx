// Hoola App Engine - locked by Hoola. The app starts in src/App.tsx.
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import App from "./App";
import "./index.css";

// The app is served under a path (the preview, or /apps/<name>/__app/ when live); Hoola writes <base href> for it.
const basename = new URL(document.baseURI).pathname.replace(/\/$/, "") || "/";
// The app runs inside its Hoola shell: the shell keeps the address bar in step with the app's page.
function NavSync() {
  const loc = useLocation();
  React.useEffect(() => {
    if (window.parent !== window) window.parent.postMessage({ hoola: "nav", path: loc.pathname + loc.search }, "*");
  }, [loc.pathname, loc.search]);
  return null;
}

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={basename}>
        <NavSync />
        <App />
        <Toaster position="top-center" />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
