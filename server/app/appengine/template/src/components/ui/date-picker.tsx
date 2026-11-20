import * as React from "react";
import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export interface DatePickerProps {
  value?: Date;
  onChange?: (d?: Date) => void;
  placeholder?: string;
  disabled?: boolean;
  /** date-fns pattern for the button text (default "d MMM yyyy") */
  dateFormat?: string;
  className?: string;
  id?: string;
}

/** A date box: a button that opens a calendar (the browser date box looks different everywhere). */
export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a date",
  disabled,
  dateFormat = "d MMM yyyy",
  className,
  id,
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="secondary"
          disabled={disabled}
          data-empty={!value}
          className={cn("w-full justify-start text-left font-normal data-[empty=true]:text-muted", className)}
        >
          <CalendarIcon className="size-4 text-muted" aria-hidden="true" />
          {value ? format(value, dateFormat) : <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value}
          defaultMonth={value}
          onSelect={(d) => {
            onChange?.(d);
            setOpen(false);
          }}
          className="rounded-card"
        />
      </PopoverContent>
    </Popover>
  );
}
