// Hoola App Engine - locked by Hoola. v0.999.64 D3: React and the islands' code, loaded only when the first island
// of a site page comes near the screen and the browser is free (islands-entry.tsx decides when).
import * as React from "react";
import { hydrateRoot, createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

type Mod = { default: React.ComponentType<Record<string, unknown>> & { raw?: React.ComponentType<Record<string, unknown>> } };
const MODS = import.meta.glob<Mod>(["./islands/**/*.tsx", "./components/**/*.tsx"]);
const basename = new URL(document.baseURI).pathname.replace(/\/$/, "") || "/";
const client = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

let toaster = false;
export async function wake(el: HTMLElement): Promise<void> {
  const load = MODS[`./${el.dataset.island || ""}.tsx`];           // "components/blocks/faq" -> its own file
  if (!load) return;
  const m = await load();
  const Comp = m.default.raw || m.default;
  let props: Record<string, unknown> = {};
  try {
    props = JSON.parse(el.dataset.props || "{}");
  } catch {
    props = {};
  }
  hydrateRoot(
    el,
    <QueryClientProvider client={client}>
      <BrowserRouter basename={basename}>
        <Comp {...props} />
      </BrowserRouter>
    </QueryClientProvider>,
    // the server rendered this island as its own root with this prefix, so its ids (labels, menus) match
    { identifierPrefix: el.dataset.idp || "", onRecoverableError: () => undefined },
  );
  if (!toaster) {
    toaster = true;                                  // toasts load after the page settles, in their own file
    void import("sonner").then(({ Toaster }) => {
      const t = document.createElement("div");
      document.body.appendChild(t);
      createRoot(t).render(<Toaster position="top-center" />);
    });
  }
}
