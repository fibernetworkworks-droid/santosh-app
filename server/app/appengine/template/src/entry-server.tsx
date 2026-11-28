// Hoola App Engine - locked by Hoola. v0.999.64 D3: the build renders every page of the app to finished HTML here
// (React on the server, in the build box, no network). The browser then has the whole page at once.
import * as React from "react";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { IslandSink, type IslandRun } from "./lib/island";
import { SeoSink, type SeoProps } from "./lib/seo";

export const BASE = "/__hoola_base__";

function Providers({ url, client, children }: { url: string; client: QueryClient; children: React.ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <StaticRouter location={BASE + url} basename={BASE}>
        {children}
      </StaticRouter>
    </QueryClientProvider>
  );
}

/** islands: true = a SITE page (each island rendered as a root of its own, the browser wakes only those);
 *  false = the whole app takes over in the browser */
export function render(url: string, opts: { islands?: boolean } = {}) {
  const seo: SeoProps[] = [];
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  const run: IslandRun = {
    on: !!opts.islands, used: new Set(), stuck: new Set(), n: 0,
    render: (node, idPrefix) =>
      renderToString(
        <SeoSink.Provider value={null}>
          <Providers url={url} client={client}>{node}</Providers>
        </SeoSink.Provider>,
        { identifierPrefix: idPrefix },
      ),
  };
  const html = renderToString(
    <React.StrictMode>
      <SeoSink.Provider value={seo}>
        <IslandSink.Provider value={run}>
          <Providers url={url} client={client}>
            <App />
          </Providers>
        </IslandSink.Provider>
      </SeoSink.Provider>
    </React.StrictMode>,
  );
  const head: SeoProps = {};
  for (const s of seo) Object.assign(head, Object.fromEntries(Object.entries(s).filter(([, v]) => v !== undefined)));
  return { html, head, islands: [...run.used], stuck: [...run.stuck], app: html.includes("data-hoola-app") };
}
