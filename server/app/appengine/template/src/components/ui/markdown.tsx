import * as React from "react";
import Markdown from "markdown-to-jsx";
import { cn } from "@/lib/utils";

const a = (props: React.AnchorHTMLAttributes<HTMLAnchorElement>) => {
  const outside = /^https?:/i.test(String(props.href || ""));
  return <a {...props} className="text-primary underline underline-offset-4" {...(outside ? { target: "_blank", rel: "noopener noreferrer" } : {})} />;
};

/**
 * Formatted text from Markdown (help pages, notes, answers, product descriptions) in the app's own type. Raw HTML inside
 * the text is never run or drawn (safe for text people type); links to other sites open in a new tab.
 *   <Prose text={page.body} />
 */
export function Prose({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("max-w-prose space-y-4 leading-relaxed text-ink", className)}>
      <Markdown
        options={{
          disableParsingRawHTML: true,
          forceBlock: true,
          overrides: {
            h1: { props: { className: "font-head text-3xl font-semibold tracking-tight" } },
            h2: { props: { className: "font-head text-2xl font-semibold tracking-tight pt-2" } },
            h3: { props: { className: "font-head text-xl font-semibold pt-1" } },
            p: { props: { className: "leading-relaxed" } },
            ul: { props: { className: "list-disc space-y-1 pl-6" } },
            ol: { props: { className: "list-decimal space-y-1 pl-6" } },
            blockquote: { props: { className: "border-l-2 border-line pl-4 text-muted" } },
            code: { props: { className: "rounded-control bg-ink/5 px-1.5 py-0.5 font-mono text-sm" } },
            pre: { props: { className: "overflow-x-auto rounded-card bg-ink/5 p-4 text-sm" } },
            hr: { props: { className: "border-line" } },
            table: { props: { className: "w-full text-sm" } },
            th: { props: { className: "border-b border-line py-2 text-left font-medium" } },
            td: { props: { className: "border-b border-line py-2" } },
            a: { component: a },
            img: { props: { className: "rounded-card", loading: "lazy" } },
          },
        }}
      >
        {text || ""}
      </Markdown>
    </div>
  );
}
