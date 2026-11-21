// Hoola App Engine - locked by Hoola. v0.999.64 D3: a page tells search engines and link previews what it is.
//   <Seo title="Dental clinic in Nagpur" description="..." jsonLd={{ "@type": "Dentist", ... }} />
// Put ONE <Seo> on every page. On a pre-rendered page Hoola writes it into the page's <head> (title, description,
// canonical link, Open Graph, JSON-LD) at build; in the browser it keeps the tab title in step.
import * as React from "react";

export interface SeoProps {
  title?: string;
  description?: string;
  image?: string;
  /** structured data (schema.org), one object or a list */
  jsonLd?: Record<string, unknown> | Record<string, unknown>[];
  /** a page that should never show in search (thank-you pages, account pages) */
  noindex?: boolean;
  /** v0.999.77 D8: the page's language (<html lang>, e.g. "hi") and the same page in the site's other languages */
  lang?: string;
  alternates?: { hreflang: string; href: string }[];
}

export const SeoSink = React.createContext<SeoProps[] | null>(null);

export function Seo(props: SeoProps) {
  const sink = React.useContext(SeoSink);
  if (sink) sink.push(props);
  React.useEffect(() => {
    if (props.title) document.title = props.title;
    if (props.lang) document.documentElement.lang = props.lang;
    if (props.description) {
      let m = document.querySelector('meta[name="description"]');
      if (!m) {
        m = document.createElement("meta");
        m.setAttribute("name", "description");
        document.head.appendChild(m);
      }
      m.setAttribute("content", props.description);
    }
  }, [props.title, props.description, props.lang]);
  return null;
}

/** v0.999.64 D3: wrap a page that needs a signed-in visitor or live data. On a site, such a page runs as the full
 *  app (inside the app's sealed frame, with its sign-in); every other page stays plain HTML with islands. */
export function AppPage({ children }: { children: React.ReactNode }) {
  return <div data-hoola-app="" style={{ display: "contents" }}>{children}</div>;
}
