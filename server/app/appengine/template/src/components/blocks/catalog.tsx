// v0.999.80 D8 wave 4 block: Catalogue - her products / doctors / properties / courses from her sheet, the same items
// and the same addresses as her HTML website's catalogue (site/catalog.py): a listing of 48 a page with numbered pages,
// and one page per item (photo, price, her columns, description, back to the list). Hoola writes each list's items as
// a data file (src/data/catalog/<list>.json); these two views draw it. Every page is pre-rendered for search engines.
import * as React from "react";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Section, Container, Picture } from "./_kit";

export interface CatalogEntry {
  s: string;
  t: string;
  p: string;
  img: string;
  sub: string;
  d: string;
  f: string[][];
  ni: boolean;
}

export interface CatalogData {
  key: string;
  label: string;
  itemLabel: string;
  per: number;
  items: CatalogEntry[];
}

export const pagesOf = (d: CatalogData) => Math.max(1, Math.ceil(d.items.length / (d.per || 48)));
export const pageHref = (d: CatalogData, n: number) => (n <= 1 ? `./${d.key}` : `./${d.key}/page/${n}`);
export const findItem = (d: CatalogData, slug?: string) => d.items.find((x) => x.s === slug);

function Pager({ data, page }: { data: CatalogData; page: number }) {
  const total = pagesOf(data);
  if (total <= 1) return null;
  const nums = Array.from(new Set([1, total, ...Array.from({ length: 5 }, (_, i) => page - 2 + i)]))
    .filter((k) => k >= 1 && k <= total).sort((a, b) => a - b);
  const link = "inline-flex min-h-10 min-w-10 items-center justify-center gap-1 rounded-control px-3 text-sm no-underline transition-colors hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";
  return (
    <nav aria-label="Pages" className="mt-12 flex flex-wrap items-center gap-1">
      {page > 1 ? <a rel="prev" href={pageHref(data, page - 1)} className={cn(link, "text-ink")}><ChevronLeft className="size-4" aria-hidden="true" />Previous</a> : null}
      {nums.map((k, i) => (
        <React.Fragment key={k}>
          {i > 0 && k - nums[i - 1] > 1 ? <span aria-hidden="true" className="px-1 text-muted">…</span> : null}
          <a href={pageHref(data, k)} aria-current={k === page ? "page" : undefined}
            className={cn(link, k === page ? "bg-primary text-primary-ink hover:bg-primary" : "text-ink")}>{k}</a>
        </React.Fragment>
      ))}
      {page < total ? <a rel="next" href={pageHref(data, page + 1)} className={cn(link, "text-ink")}>Next<ChevronRight className="size-4" aria-hidden="true" /></a> : null}
    </nav>
  );
}

export function CatalogList({ data, page }: { data: CatalogData; page: number }) {
  const per = data.per || 48;
  const items = data.items.slice((page - 1) * per, page * per);
  return (
    <Section block="catalog" variant="list" tone="plain">
      <Container>
        <div className="mb-10 flex flex-col gap-2">
          <h1 className="font-head text-3xl font-semibold tracking-tight sm:text-4xl">{data.label}</h1>
          <p className="text-muted">{data.items.length} {data.itemLabel || "items"}{pagesOf(data) > 1 ? ` · page ${page} of ${pagesOf(data)}` : ""}</p>
        </div>
        <ul className="grid grid-cols-2 gap-4 sm:gap-6 md:grid-cols-3 lg:grid-cols-4">
          {items.map((it, i) => (
            <li key={it.s}>
              <a href={`./${data.key}/${it.s}`} className="group flex h-full flex-col gap-3 rounded-card no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                {it.img ? <img src={it.img} alt={it.t} loading={i < 4 ? "eager" : "lazy"} className="aspect-square w-full rounded-card object-cover" />
                  : <Picture alt={it.t} ratio="1/1" label={it.t} />}
                <span className="font-medium text-ink group-hover:text-primary">{it.t}</span>
                {it.p ? <span className="font-semibold tabular-nums">{it.p}</span> : null}
                {it.sub ? <span className="text-sm text-muted">{it.sub}</span> : null}
              </a>
            </li>
          ))}
        </ul>
        <Pager data={data} page={page} />
      </Container>
    </Section>
  );
}

export function CatalogItem({ data, item }: { data: CatalogData; item?: CatalogEntry }) {
  return (
    <Section block="catalog" variant="item" tone="plain">
      <Container>
        <a href={pageHref(data, 1)} className="inline-flex items-center gap-1.5 text-sm font-medium text-muted no-underline transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
          <ArrowLeft className="size-4" aria-hidden="true" />
          All {data.label.toLowerCase()}
        </a>
        {!item ? (
          <p className="mt-10 text-lg text-muted">This one is not in the list any more.</p>
        ) : (
          <div className="mt-8 grid gap-10 md:grid-cols-2 md:gap-14">
            {item.img ? <img src={item.img} alt={item.t} className="aspect-square w-full rounded-card object-cover" />
              : <Picture alt={item.t} ratio="1/1" label={item.t} />}
            <div className="flex flex-col gap-5">
              <h1 className="text-balance font-head text-3xl font-semibold tracking-tight sm:text-4xl">{item.t}</h1>
              {item.p ? <p className="font-head text-2xl font-semibold tabular-nums text-primary">{item.p}</p> : null}
              {item.d ? <p className="max-w-prose text-lg leading-relaxed text-muted">{item.d}</p> : null}
              {item.f.length ? (
                <dl className="grid gap-3 border-t border-line pt-5 sm:grid-cols-2">
                  {item.f.map(([k, v]) => (
                    <div key={k} className="flex flex-col gap-0.5">
                      <dt className="text-sm text-muted">{k}</dt>
                      <dd className="font-medium">{v}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}
            </div>
          </div>
        )}
      </Container>
    </Section>
  );
}
