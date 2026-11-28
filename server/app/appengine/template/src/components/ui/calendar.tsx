import * as React from "react";
import { DayPicker, getDefaultClassNames, type DayButton } from "react-day-picker";
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { buttonVariants } from "@/components/ui/button";

export type CalendarProps = React.ComponentProps<typeof DayPicker>;

export function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  captionLayout = "label",
  components,
  ...props
}: CalendarProps) {
  const d = getDefaultClassNames();
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      captionLayout={captionLayout}
      className={cn("w-fit bg-surface p-3 text-ink", className)}
      classNames={{
        root: cn("w-fit", d.root),
        months: cn("relative flex flex-col gap-4 sm:flex-row", d.months),
        month: cn("flex w-full flex-col gap-4", d.month),
        nav: cn("absolute inset-x-0 top-0 flex w-full items-center justify-between gap-1", d.nav),
        button_previous: cn(
          buttonVariants({ variant: "ghost", size: "icon-sm" }),
          "p-0 aria-disabled:opacity-50",
          d.button_previous,
        ),
        button_next: cn(buttonVariants({ variant: "ghost", size: "icon-sm" }), "p-0 aria-disabled:opacity-50", d.button_next),
        month_caption: cn("flex h-8 w-full items-center justify-center px-8", d.month_caption),
        dropdowns: cn("flex h-8 w-full items-center justify-center gap-1.5 text-sm font-medium", d.dropdowns),
        dropdown_root: cn(
          "relative rounded-control border border-line has-focus:outline-2 has-focus:outline-primary",
          d.dropdown_root,
        ),
        dropdown: cn("absolute inset-0 opacity-0", d.dropdown),
        caption_label: cn(
          "font-medium select-none",
          captionLayout === "label"
            ? "text-sm"
            : "flex h-8 items-center gap-1 rounded-control pl-2 pr-1 text-sm [&>svg]:size-3.5 [&>svg]:text-muted",
          d.caption_label,
        ),
        month_grid: cn("w-full border-collapse", d.month_grid),
        weekdays: cn("flex", d.weekdays),
        weekday: cn("flex-1 rounded-control text-xs font-normal text-muted select-none", d.weekday),
        week: cn("mt-1 flex w-full", d.week),
        week_number_header: cn("w-9 select-none", d.week_number_header),
        week_number: cn("text-xs text-muted select-none", d.week_number),
        day: cn(
          "group/day relative aspect-square h-full w-full p-0 text-center select-none [&:first-child[data-selected=true]_button]:rounded-l-control [&:last-child[data-selected=true]_button]:rounded-r-control",
          d.day,
        ),
        range_start: cn("rounded-l-control bg-primary/10", d.range_start),
        range_middle: cn("rounded-none", d.range_middle),
        range_end: cn("rounded-r-control bg-primary/10", d.range_end),
        today: cn("rounded-control bg-ink/5 data-[selected=true]:rounded-none", d.today),
        outside: cn("text-muted aria-selected:text-muted", d.outside),
        disabled: cn("text-muted opacity-50", d.disabled),
        hidden: cn("invisible", d.hidden),
        ...classNames,
      }}
      components={{
        Chevron: ({ className: c, orientation, ...rest }) => {
          const Icon = orientation === "left" ? ChevronLeft : orientation === "right" ? ChevronRight : ChevronDown;
          return <Icon className={cn("size-4", c)} aria-hidden="true" {...rest} />;
        },
        DayButton: CalendarDayButton,
        ...components,
      }}
      {...props}
    />
  );
}

export function CalendarDayButton({ className, day, modifiers, ...props }: React.ComponentProps<typeof DayButton>) {
  const ref = React.useRef<HTMLButtonElement>(null);
  React.useEffect(() => {
    if (modifiers.focused) ref.current?.focus();
  }, [modifiers.focused]);
  const single = modifiers.selected && !modifiers.range_start && !modifiers.range_end && !modifiers.range_middle;
  return (
    <button
      ref={ref}
      type="button"
      data-day={day.date.toLocaleDateString()}
      data-selected-single={single}
      data-range-start={modifiers.range_start}
      data-range-end={modifiers.range_end}
      data-range-middle={modifiers.range_middle}
      className={cn(
        "inline-flex aspect-square size-auto w-full min-w-9 items-center justify-center rounded-control text-sm font-normal leading-none text-ink transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary disabled:pointer-events-none group-data-[outside=true]/day:text-muted data-[range-end=true]:bg-primary data-[range-end=true]:text-primary-ink data-[range-middle=true]:rounded-none data-[range-middle=true]:bg-primary/10 data-[range-middle=true]:text-ink data-[range-start=true]:bg-primary data-[range-start=true]:text-primary-ink data-[selected-single=true]:bg-primary data-[selected-single=true]:text-primary-ink",
        className,
      )}
      {...props}
    />
  );
}
