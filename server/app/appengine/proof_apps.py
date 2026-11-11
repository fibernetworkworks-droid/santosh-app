"""v0.814 the five card asks of L8 ("5 card asks built in the box"), each with the files an engineer would write.

The files are fixed here (no model call): the proof is about the ENGINE - the tool's rules, the box build, the
preview, the publish - not about a model's taste. Every app keeps its data on the page and says "Sample data"
(Hoola Cloud is not connected yet). `must` = words the rendered page must show; `click` = a button the walk presses
and the words that must appear after it."""
from __future__ import annotations

ASKS = [
    {"key": "tasks", "name": "Shop staff tasks", "palette": "calm",
     "brief": "A task list for my shop staff: add a task, mark it done, see what is left.",
     "must": ["Shop staff tasks", "Sample data"], "click": ("Add task", "Count the cash drawer"),
     "files": {
         "src/App.tsx": '''import { Routes, Route } from "react-router-dom";
import Tasks from "./pages/Tasks";

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<Tasks />} />
    </Routes>
  );
}
''',
         "src/pages/Tasks.tsx": '''import { useState } from "react";
import { Check, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

type Task = { id: number; title: string; done: boolean };
const START: Task[] = [
  { id: 1, title: "Open the shutter and switch on the lights", done: true },
  { id: 2, title: "Fill the sweets display", done: false },
];

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>(START);
  const [title, setTitle] = useState("Count the cash drawer");
  const left = tasks.filter((t) => !t.done).length;

  function add() {
    const t = title.trim();
    if (!t) return;
    setTasks((all) => [...all, { id: Date.now(), title: t, done: false }]);
    setTitle("");
    toast.success("Task added");
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>Shop staff tasks</CardTitle>
          <CardDescription>
            {left} left today <Badge>Sample data</Badge>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="A new task" aria-label="New task" />
            <Button onClick={add}>
              <Plus size={16} /> Add task
            </Button>
          </div>
          <ul className="divide-y divide-line">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-3 py-3">
                <span className={t.done ? "text-muted line-through" : "text-ink"}>{t.title}</span>
                <Button variant={t.done ? "secondary" : "primary"} size="sm"
                  onClick={() => setTasks((all) => all.map((x) => (x.id === t.id ? { ...x, done: !x.done } : x)))}>
                  <Check size={14} /> {t.done ? "Undo" : "Done"}
                </Button>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </main>
  );
}
''',
     }},
    {"key": "clinic", "name": "Clinic appointment request", "palette": "fresh",
     "brief": "A page where patients ask for an appointment: name, 10-digit mobile, date, morning or evening. We call back to confirm.",
     "must": ["Ask for an appointment", "we call you back"], "click": ("Send request", "Enter your name"),
     "files": {
         "src/App.tsx": '''import { Routes, Route } from "react-router-dom";
import Book from "./pages/Book";
import Thanks from "./pages/Thanks";

export default function App() {
  return (
    <Routes>
      <Route path="/thanks" element={<Thanks />} />
      <Route path="*" element={<Book />} />
    </Routes>
  );
}
''',
         "src/pages/Book.tsx": '''import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  name: z.string().min(2, "Enter your name"),
  mobile: z.string().regex(/^[6-9][0-9]{9}$/, "Enter a 10-digit mobile number"),
  date: z.string().min(1, "Pick a date"),
  slot: z.enum(["morning", "evening"]),
});
type Form = z.infer<typeof schema>;

export default function Book() {
  const nav = useNavigate();
  const { register, handleSubmit, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", mobile: "", date: "", slot: "morning" },
  });
  return (
    <main className="mx-auto max-w-lg px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>Ask for an appointment</CardTitle>
          <CardDescription>This is a request - we call you back to confirm the time.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" noValidate onSubmit={handleSubmit(() => nav("/thanks"))}>
            <div className="space-y-1">
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...register("name")} />
              {errors.name && <p className="text-sm text-bad">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="mobile">Mobile</Label>
              <Input id="mobile" inputMode="numeric" {...register("mobile")} />
              {errors.mobile && <p className="text-sm text-bad">{errors.mobile.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="date">Date</Label>
              <Input id="date" type="date" {...register("date")} />
              {errors.date && <p className="text-sm text-bad">{errors.date.message}</p>}
            </div>
            <fieldset className="space-y-1">
              <legend className="text-sm font-medium text-ink">Time</legend>
              <label className="mr-4 text-sm"><input type="radio" value="morning" {...register("slot")} /> Morning</label>
              <label className="text-sm"><input type="radio" value="evening" {...register("slot")} /> Evening</label>
            </fieldset>
            <Button type="submit" className="w-full">Send request</Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
''',
         "src/pages/Thanks.tsx": '''import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Thanks() {
  return (
    <main className="mx-auto max-w-lg px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle>Request received</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-muted">We call you back to confirm the time.</p>
          <Link to="/">Ask for another time</Link>
        </CardContent>
      </Card>
    </main>
  );
}
''',
     }},
    {"key": "sales", "name": "Sales dashboard", "palette": "night",
     "brief": "A dashboard with this week's sales by day, orders, average bill and a chart.",
     "must": ["Sales this week", "Sample data", "Average bill"], "click": ("By product", "Kaju katli"),
     "files": {
         "src/App.tsx": '''import { Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<Dashboard />} />
    </Routes>
  );
}
''',
         "src/lib/money.ts": '''export const rupees = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
''',
         "src/pages/Dashboard.tsx": '''import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Table, TableCell, TableHead } from "@/components/ui/table";
import { rupees } from "@/lib/money";

const DAYS = [
  { day: "Mon", sales: 18400, orders: 52 }, { day: "Tue", sales: 15200, orders: 44 },
  { day: "Wed", sales: 21100, orders: 61 }, { day: "Thu", sales: 19800, orders: 57 },
  { day: "Fri", sales: 26500, orders: 73 }, { day: "Sat", sales: 33900, orders: 92 },
  { day: "Sun", sales: 29700, orders: 81 },
];
const PRODUCTS = [
  { name: "Kaju katli", sales: 41200 }, { name: "Motichoor laddoo", sales: 28700 }, { name: "Rasgulla", sales: 19300 },
];

export default function Dashboard() {
  const total = DAYS.reduce((a, d) => a + d.sales, 0);
  const orders = DAYS.reduce((a, d) => a + d.orders, 0);
  const kpis = [
    { label: "Sales this week", value: rupees(total) },
    { label: "Orders", value: String(orders) },
    { label: "Average bill", value: rupees(Math.round(total / orders)) },
  ];
  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Sales this week</h1>
        <Badge tone="warn">Sample data</Badge>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardHeader>
              <CardDescription>{k.label}</CardDescription>
              <CardTitle className="text-2xl">{k.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>
      <Tabs defaultValue="days">
        <TabsList>
          <TabsTrigger value="days">By day</TabsTrigger>
          <TabsTrigger value="products">By product</TabsTrigger>
        </TabsList>
        <TabsContent value="days">
          <Card>
            <CardContent className="h-72 pt-6">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={DAYS}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-line)" />
                  <XAxis dataKey="day" stroke="var(--color-muted)" />
                  <YAxis stroke="var(--color-muted)" />
                  <Tooltip />
                  <Bar dataKey="sales" fill="var(--color-primary)" radius={6} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="products">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <thead><tr><TableHead>Product</TableHead><TableHead>Sales</TableHead></tr></thead>
                <tbody>
                  {PRODUCTS.map((p) => (
                    <tr key={p.name}><TableCell>{p.name}</TableCell><TableCell>{rupees(p.sales)}</TableCell></tr>
                  ))}
                </tbody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </main>
  );
}
''',
     }},
    {"key": "shop", "name": "Mithai catalogue", "palette": "warm",
     "brief": "A product catalogue: sweets with prices per kg, add to a cart, see the total.",
     "must": ["Our sweets", "Sample data"], "click": ("Add Kaju katli", "Cart (1)"),
     "files": {
         "src/App.tsx": '''import { Routes, Route } from "react-router-dom";
import Shop from "./pages/Shop";

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<Shop />} />
    </Routes>
  );
}
''',
         "src/lib/cart.ts": '''export type Item = { id: string; name: string; price: number };
export type Line = Item & { qty: number };

export function addTo(lines: Line[], item: Item): Line[] {
  const found = lines.find((l) => l.id === item.id);
  if (found) return lines.map((l) => (l.id === item.id ? { ...l, qty: l.qty + 1 } : l));
  return [...lines, { ...item, qty: 1 }];
}

export const totalOf = (lines: Line[]) => lines.reduce((a, l) => a + l.price * l.qty, 0);
export const rupees = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
''',
         "src/pages/Shop.tsx": '''import { useState } from "react";
import { ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { addTo, rupees, totalOf, type Item, type Line } from "@/lib/cart";

const ITEMS: Item[] = [
  { id: "kaju", name: "Kaju katli", price: 1100 },
  { id: "laddoo", name: "Motichoor laddoo", price: 560 },
  { id: "peda", name: "Mathura peda", price: 640 },
];

export default function Shop() {
  const [lines, setLines] = useState<Line[]>([]);
  const count = lines.reduce((a, l) => a + l.qty, 0);
  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold">Our sweets</h1>
          <p className="text-muted">Prices per kg <Badge>Sample data</Badge></p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="secondary"><ShoppingBag size={16} /> Cart ({count})</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle className="font-head text-lg font-semibold">Your cart</DialogTitle>
            <DialogDescription className="text-sm text-muted">Orders are not taken online yet.</DialogDescription>
            <ul className="my-4 space-y-2">
              {lines.map((l) => (
                <li key={l.id} className="flex justify-between"><span>{l.name} x {l.qty}</span><span>{rupees(l.price * l.qty)}</span></li>
              ))}
            </ul>
            <p className="font-semibold">Total {rupees(totalOf(lines))}</p>
          </DialogContent>
        </Dialog>
      </header>
      <div className="grid gap-4 sm:grid-cols-3">
        {ITEMS.map((it) => (
          <Card key={it.id}>
            <CardHeader>
              <CardTitle>{it.name}</CardTitle>
              <CardDescription>{rupees(it.price)} / kg</CardDescription>
            </CardHeader>
            <CardContent />
            <CardFooter>
              <Button className="w-full" onClick={() => setLines((ls) => addTo(ls, it))}>Add {it.name}</Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </main>
  );
}
''',
     }},
    {"key": "batches", "name": "Coaching batch timetable", "palette": "bold",
     "brief": "A timetable of my coaching batches by subject, with start dates and seats left.",
     "must": ["Batch timetable", "Sample data"], "click": ("Physics", "JEE Physics A"),
     "files": {
         "src/App.tsx": '''import { Routes, Route } from "react-router-dom";
import Timetable from "./pages/Timetable";

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<Timetable />} />
    </Routes>
  );
}
''',
         "src/pages/Timetable.tsx": '''import { format, parseISO } from "date-fns";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableCell, TableHead } from "@/components/ui/table";

type Batch = { name: string; subject: "Maths" | "Physics" | "Chemistry"; starts: string; time: string; seats: number };
const BATCHES: Batch[] = [
  { name: "JEE Maths A", subject: "Maths", starts: "2026-12-01", time: "7:00 am", seats: 6 },
  { name: "JEE Physics A", subject: "Physics", starts: "2026-12-03", time: "5:30 pm", seats: 0 },
  { name: "NEET Chemistry B", subject: "Chemistry", starts: "2026-12-05", time: "4:00 pm", seats: 12 },
];
const SUBJECTS = ["Maths", "Physics", "Chemistry"] as const;

export default function Timetable() {
  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <div className="flex items-center gap-3">
        <h1 className="text-3xl font-semibold">Batch timetable</h1>
        <Badge>Sample data</Badge>
      </div>
      <Tabs defaultValue="Maths">
        <TabsList>
          {SUBJECTS.map((s) => <TabsTrigger key={s} value={s}>{s}</TabsTrigger>)}
        </TabsList>
        {SUBJECTS.map((s) => (
          <TabsContent key={s} value={s}>
            <Card>
              <CardHeader><CardTitle>{s} batches</CardTitle></CardHeader>
              <CardContent>
                <Table>
                  <thead><tr><TableHead>Batch</TableHead><TableHead>Starts</TableHead><TableHead>Time</TableHead><TableHead>Seats</TableHead></tr></thead>
                  <tbody>
                    {BATCHES.filter((b) => b.subject === s).map((b) => (
                      <tr key={b.name}>
                        <TableCell>{b.name}</TableCell>
                        <TableCell>{format(parseISO(b.starts), "d MMM yyyy")}</TableCell>
                        <TableCell>{b.time}</TableCell>
                        <TableCell>{b.seats ? <Badge tone="ok">{b.seats} left</Badge> : <Badge tone="bad">Full</Badge>}</TableCell>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </main>
  );
}
''',
     }},
]

# Writes the rules must refuse (each changes nothing): the proof counts them.
TRAPS = [
    ("src/pages/Bad1.tsx", 'export default function B() { return <p className="text-[#ff0000]">x</p>; }\n', "one-off value"),
    ("src/pages/Bad2.tsx", 'export default function B() { return <p className="bg-blue-500">x</p>; }\n', "palette colour"),
    ("src/pages/Bad3.tsx", 'export default function B() { return <p style={{ color: "#ff0000" }}>x</p>; }\n', "raw colour"),
    ("src/pages/Bad4.tsx", 'fetch("https://example.com/api");\nexport default function B() { return null; }\n', "unsafe"),
    ("src/pages/Bad5.tsx", 'import axios from "axios";\nexport default function B() { return null; }\n', "import"),
    ("src/pages/Bad6.tsx", 'export default function B() { return <div dangerouslySetInnerHTML={{ __html: "x" }} />; }\n', "unsafe"),
    ("vite.config.ts", "export default {};\n", "locked"),
    ("../../etc/passwd", "x\n", "path"),
]
