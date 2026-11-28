import * as React from "react";
import { Calendar, dateFnsLocalizer, Views, type View } from "react-big-calendar";
import { format, getDay, parse, startOfWeek } from "date-fns";
import { enIN } from "date-fns/locale";
import "react-big-calendar/lib/css/react-big-calendar.css";
import "./schedule.css";

const localizer = dateFnsLocalizer({ format, parse, startOfWeek, getDay, locales: { "en-IN": enIN } });

/** One booking / shift / class on the calendar. */
export type ScheduleEvent = { id: string; title: string; start: Date; end: Date; allDay?: boolean; resource?: unknown };

/**
 * Month / week / day / agenda views for bookings, schedules, staff rotas and classes (react-big-calendar), in the app's
 * own colours. Example:
 *   <Schedule events={slots} onSelectEvent={(e) => open(e.id)} onSelectSlot={({ start, end }) => book(start, end)} />
 */
export function Schedule({
  events,
  view: initialView = Views.WEEK,
  views = [Views.MONTH, Views.WEEK, Views.DAY, Views.AGENDA],
  onSelectEvent,
  onSelectSlot,
  height = 640,
  min,
  max,
}: {
  events: ScheduleEvent[];
  view?: View;
  views?: View[];
  onSelectEvent?: (e: ScheduleEvent) => void;
  /** set it to let people pick a free time by dragging across the calendar */
  onSelectSlot?: (slot: { start: Date; end: Date }) => void;
  height?: number;
  /** the first and last hour shown in week / day view, e.g. new Date(0, 0, 0, 8) */
  min?: Date;
  max?: Date;
}) {
  const [view, setView] = React.useState<View>(initialView);
  const [date, setDate] = React.useState(new Date());
  return (
    <div className="hoola-schedule rounded-card border border-line bg-surface p-3" style={{ height }}>
      <Calendar
        localizer={localizer}
        culture="en-IN"
        events={events}
        startAccessor="start"
        endAccessor="end"
        titleAccessor="title"
        allDayAccessor="allDay"
        view={view}
        onView={setView}
        views={views}
        date={date}
        onNavigate={setDate}
        onSelectEvent={onSelectEvent ? (e) => onSelectEvent(e as ScheduleEvent) : undefined}
        selectable={!!onSelectSlot}
        onSelectSlot={onSelectSlot ? (s) => onSelectSlot({ start: s.start as Date, end: s.end as Date }) : undefined}
        min={min}
        max={max}
        popup
      />
    </div>
  );
}
