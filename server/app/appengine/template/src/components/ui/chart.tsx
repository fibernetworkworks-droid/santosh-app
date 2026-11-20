import * as React from "react";
import { Legend, ResponsiveContainer, Tooltip } from "recharts";
import { cn } from "@/lib/utils";

/** The chart colours, in order: the app's own tokens, never raw colours. Series i uses CHART_COLORS[i % 5]. */
export const CHART_COLORS = [
  "var(--color-primary)",
  "var(--color-accent)",
  "var(--color-ok)",
  "var(--color-warn)",
  "var(--color-muted)",
] as const;

export function chartColor(i: number): string {
  return CHART_COLORS[((i % CHART_COLORS.length) + CHART_COLORS.length) % CHART_COLORS.length];
}

/** shadcn's chart config: a label (and optional colour) per data key. */
export type ChartConfig = Record<string, { label?: React.ReactNode; color?: string; icon?: React.ComponentType }>;

/** recharts' own Tooltip and Legend under shadcn's names: <ChartTooltip content={<ChartTooltipContent />} />. */
export const ChartTooltip = Tooltip;
export const ChartLegend = Legend;

const TOKEN_NAMES = new Set(["bg", "surface", "ink", "muted", "line", "primary", "primary-ink", "accent", "ok", "warn", "bad"]);

const ChartContext = React.createContext<{ config: ChartConfig }>({ config: {} });

export function useChart() {
  return React.useContext(ChartContext);
}

export interface ChartContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  /** the chart's height in px (the width follows its box) */
  height?: number;
  config?: ChartConfig;
  /** one recharts chart, e.g. <BarChart data={rows}>...</BarChart> */
  children: React.ReactElement;
}

/**
 * The box every chart sits in: a fixed height, the axes / grid / tooltip cursor in the app's tokens, and
 * `var(--color-<key>)` for each key of `config` (keys that are token names are left to the tokens).
 */
export const ChartContainer = React.forwardRef<HTMLDivElement, ChartContainerProps>(
  ({ height = 280, config = {}, className, style, children, ...props }, ref) => {
    const vars: Record<string, string> = {};
    Object.entries(config).forEach(([key, item], i) => {
      if (!TOKEN_NAMES.has(key)) vars[`--color-${key}`] = item.color ?? chartColor(i);
    });
    return (
      <ChartContext.Provider value={{ config }}>
        <div
          ref={ref}
          data-slot="chart"
          className={cn(
            "w-full text-xs text-muted [&_.recharts-cartesian-axis-tick_text]:fill-muted [&_.recharts-cartesian-grid_line]:stroke-line [&_.recharts-curve.recharts-tooltip-cursor]:stroke-line [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-ink/5 [&_.recharts-polar-grid_[stroke]]:stroke-line [&_.recharts-reference-line_[stroke]]:stroke-line [&_.recharts-dot[stroke]]:stroke-surface [&_.recharts-sector]:outline-none [&_.recharts-surface]:outline-none [&_.recharts-layer]:outline-none",
            className,
          )}
          style={{ height, ...vars, ...style } as React.CSSProperties}
          {...props}
        >
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        </div>
      </ChartContext.Provider>
    );
  },
);
ChartContainer.displayName = "ChartContainer";

type TooltipItem = {
  name?: string | number;
  dataKey?: string | number | ((obj: unknown) => unknown);
  value?: unknown;
  color?: string;
  fill?: string;
  stroke?: string;
};

export interface ChartTooltipContentProps {
  /** filled in by recharts' <Tooltip content={<ChartTooltipContent />} /> */
  active?: boolean;
  payload?: ReadonlyArray<TooltipItem>;
  label?: React.ReactNode;
  hideLabel?: boolean;
  hideIndicator?: boolean;
  /** turn a value into text, e.g. (v) => `Rs ${v}` */
  valueFormatter?: (value: number | string) => React.ReactNode;
  labelFormatter?: (label: React.ReactNode) => React.ReactNode;
  className?: string;
}

/** The tooltip card, in the app's tokens. Use: <Tooltip content={<ChartTooltipContent />} />. */
export function ChartTooltipContent({
  active,
  payload,
  label,
  hideLabel = false,
  hideIndicator = false,
  valueFormatter,
  labelFormatter,
  className,
}: ChartTooltipContentProps) {
  const { config } = useChart();
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      className={cn(
        "grid min-w-32 gap-1.5 rounded-control border border-line bg-surface px-2.5 py-1.5 text-xs text-ink shadow-card",
        className,
      )}
    >
      {!hideLabel && label !== undefined && label !== null && label !== "" && (
        <div className="font-medium">{labelFormatter ? labelFormatter(label) : label}</div>
      )}
      <div className="grid gap-1">
        {payload.map((item, i) => {
          const key = String(typeof item.dataKey === "function" ? item.name ?? i : item.dataKey ?? item.name ?? i);
          const name = config[key]?.label ?? item.name ?? key;
          const colour = item.color ?? item.fill ?? item.stroke ?? chartColor(i);
          const raw = item.value;
          const shown =
            typeof raw === "number" || typeof raw === "string"
              ? valueFormatter
                ? valueFormatter(raw)
                : typeof raw === "number"
                  ? raw.toLocaleString()
                  : raw
              : null;
          return (
            <div key={`${key}-${i}`} className="flex items-center gap-2">
              {!hideIndicator && (
                <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: colour }} aria-hidden="true" />
              )}
              <span className="flex-1 text-muted">{name}</span>
              <span className="font-medium tabular-nums text-ink">{shown}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export interface ChartLegendContentProps {
  payload?: ReadonlyArray<{ value?: unknown; dataKey?: unknown; color?: string }>;
  className?: string;
}

/** The legend row, in the app's tokens. Use: <Legend content={<ChartLegendContent />} />. */
export function ChartLegendContent({ payload, className }: ChartLegendContentProps) {
  const { config } = useChart();
  if (!payload || payload.length === 0) return null;
  return (
    <div className={cn("flex flex-wrap items-center justify-center gap-4 pt-3 text-xs", className)}>
      {payload.map((item, i) => {
        const key = String(item.dataKey ?? item.value ?? i);
        return (
          <div key={`${key}-${i}`} className="flex items-center gap-1.5 text-muted">
            <span
              className="size-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: item.color ?? chartColor(i) }}
              aria-hidden="true"
            />
            {config[key]?.label ?? String(item.value ?? key)}
          </div>
        );
      })}
    </div>
  );
}
