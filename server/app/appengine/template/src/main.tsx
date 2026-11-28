// Hoola App Engine - locked by Hoola. The app starts in src/App.tsx.
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import App from "./App";
import { AppGuard } from "./components/ui/error-guard";
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

// v0.999.64 D3: the build already rendered this page to HTML; React picks it up (hydrates) instead of drawing it again.
const root = document.getElementById("root")!;
const tree = (
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={basename}>
        <NavSync />
        {/* v0.999.326 a crash anywhere shows "Something went wrong" + Try again, never a blank page */}
        <AppGuard>
          <App />
        </AppGuard>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
if (root.hasChildNodes()) ReactDOM.hydrateRoot(root, tree, { onRecoverableError: () => undefined });
else ReactDOM.createRoot(root).render(tree);
// the toasts live in their own root, so the page itself matches what the build rendered
const toasts = document.createElement("div");
document.body.appendChild(toasts);
ReactDOM.createRoot(toasts).render(<Toaster position="top-center" />);
