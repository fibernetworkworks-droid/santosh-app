import * as React from "react";
import { ErrorBoundary, type FallbackProps } from "react-error-boundary";
import { RotateCcw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

function Fallback({ resetErrorBoundary, whole }: FallbackProps & { whole?: boolean }) {
  return (
    <div role="alert" className={whole ? "grid min-h-screen place-items-center p-6" : "rounded-card border border-line bg-surface p-5"}>
      <div className="flex max-w-md flex-col items-center gap-3 text-center">
        <TriangleAlert className="h-6 w-6 text-warn" aria-hidden />
        <p className="font-head text-lg font-semibold text-ink">{whole ? "Something went wrong" : "This part could not be shown"}</p>
        <p className="text-sm text-muted">{whole ? "The page hit a problem. Try again; if it keeps happening, come back a little later." : "The rest of the page still works."}</p>
        <Button variant="outline" size="sm" onClick={resetErrorBoundary}>
          <RotateCcw className="h-4 w-4" aria-hidden />
          Try again
        </Button>
      </div>
    </div>
  );
}

// the error still reaches Hoola: in the Studio preview console.error goes to the error collector (file + line)
const report = (error: unknown, info: React.ErrorInfo) => console.error(error, info.componentStack);

/**
 * Wrap a part that might break (a chart fed by data, a widget) so a crash there shows a small "could not be shown" box
 * and the rest of the page keeps working:  <Guard><SalesChart data={rows} /></Guard>
 */
export function Guard({ children, resetKeys }: { children: React.ReactNode; resetKeys?: unknown[] }) {
  return (
    <ErrorBoundary FallbackComponent={Fallback} onError={report} resetKeys={resetKeys}>
      {children}
    </ErrorBoundary>
  );
}

/** The whole app's guard (src/main.tsx uses it): a crash shows "Something went wrong" + Try again, never a blank page. */
export function AppGuard({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary fallbackRender={(p) => <Fallback {...p} whole />} onError={report}>
      {children}
    </ErrorBoundary>
  );
}
