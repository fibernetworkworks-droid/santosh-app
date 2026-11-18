"""v0.835 GHAR + SHURUAAT (L12 of docs/LOVABLE_STUDIO_PLAN.md): the Studio home's starting points.

24 hand-checked STARTERS, three for each of the eight home chips (Website, Online store, Dashboard, Booking site, Portal,
Landing page, Blog, Internal tool). A starter is a complete, specific ask (what the page is, who uses it, what it must do)
plus its own palette and layout. The Studio draws each one's thumbnail from THAT palette and layout (SVG, no image file),
so the card shows the look the ask will be built in. They are NOT already-built sites: choosing one puts its ask in the
box (she can change every word) and the normal Build runs. The 1,00,000 generated template prompts stay as "Ideas"."""
from __future__ import annotations

CHIPS = ["Website", "Online store", "Dashboard", "Booking site", "Portal", "Landing page", "Blog", "Internal tool"]
LAYOUTS = {"hero", "split", "grid", "list", "board", "chart", "form", "feed"}


def _s(id_: str, kind: str, title: str, line: str, prompt: str, bg: str, ink: str, accent: str, soft: str, layout: str) -> dict:
    return {"id": id_, "kind": kind, "title": title, "line": line, "prompt": prompt, "layout": layout,
            "palette": {"bg": bg, "ink": ink, "accent": accent, "soft": soft}}


STARTERS = [
    _s("web-sweets", "Website", "Neighbourhood sweet shop", "Menu, festival boxes, WhatsApp orders",
       "A website for a neighbourhood sweet shop: today's menu with prices, Diwali gift boxes, opening hours, a map, and a WhatsApp button to order.",
       "#FFF6EA", "#3B1F0B", "#D9531E", "#FBE3C6", "split"),
    _s("web-clinic", "Website", "Family clinic", "Doctors, timings, how to reach",
       "A website for a family clinic: the doctors and what they treat, clinic timings, location with directions, and a call button. Calm and trustworthy.",
       "#F2FAF8", "#0F3D3A", "#14877C", "#D5EFEA", "hero"),
    _s("web-studio", "Website", "Photographer's portfolio", "Work, about, contact",
       "A portfolio website for a wedding photographer: a full-screen gallery of recent work, a short about page, packages, and a contact form.",
       "#111111", "#F5F5F5", "#E8B34A", "#222222", "grid"),
    _s("shop-saree", "Online store", "Saree boutique", "Catalogue, cart, UPI and COD",
       "An online store for a saree boutique: product pages with several photos, sizes and colours, a cart, UPI and cash-on-delivery checkout, and GST invoices.",
       "#FFF4F6", "#4A1424", "#B8264F", "#F9D9E1", "grid"),
    _s("shop-grocery", "Online store", "Local grocery delivery", "Daily items, slots, WhatsApp",
       "An online store for a local grocery: categories, weights and prices, a cart with a delivery-slot picker, and cash on delivery.",
       "#F4FAEC", "#1E3A0F", "#4E9A1E", "#DDEFC6", "list"),
    _s("shop-books", "Online store", "Independent bookshop", "Shelves, search, orders",
       "An online store for an independent bookshop: search by title and author, staff picks, a cart, and pickup or courier delivery.",
       "#FBF7F0", "#2B2118", "#8A5A2B", "#EADFCB", "split"),
    _s("dash-sales", "Dashboard", "Weekly sales", "Numbers, trend, best sellers",
       "A dashboard for a shop owner: this week's sales against last week, a line chart by day, best-selling items, and low stock warnings.",
       "#F6F8FC", "#14213D", "#2F6BFF", "#DCE6FB", "chart"),
    _s("dash-fees", "Dashboard", "School fee tracker", "Who paid, who is late",
       "A dashboard for a school office: fees collected this month, a list of students with dues, and a reminder button per family.",
       "#F8F6FF", "#241A4A", "#6B4FE0", "#E4DDFB", "chart"),
    _s("dash-leads", "Dashboard", "Leads this month", "Source, status, follow-ups",
       "A dashboard for a small business: new enquiries by source, their status from new to won, and the follow-ups due today.",
       "#F2F8F7", "#12332F", "#0F9D8A", "#D4EEE9", "board"),
    _s("book-salon", "Booking site", "Salon appointments", "Services, prices, slots",
       "A booking site for a salon: services with prices, pick a stylist and a time slot, and a confirmation the owner approves.",
       "#FFF5FA", "#431030", "#C2338A", "#F8D8EA", "form"),
    _s("book-physio", "Booking site", "Physio clinic", "Sessions, availability",
       "A booking site for a physiotherapy clinic: choose a treatment, see free slots for the week, and book with name and phone.",
       "#F1F8FF", "#0D2F4F", "#1B7FD1", "#D3E8FA", "form"),
    _s("book-turf", "Booking site", "Turf and court booking", "Hourly slots, prices",
       "A booking site for a sports turf: hourly slots by day with peak and off-peak prices, advance payment link, and cancellation rules.",
       "#F2FBF1", "#143312", "#2C9C2C", "#D6F0D4", "grid"),
    _s("portal-student", "Portal", "Student and parent portal", "Marks, fees, notices",
       "A portal for a coaching class: students and parents sign in, see attendance, test marks and fee status, and read notices from teachers.",
       "#F5F7FF", "#1A2250", "#3D55D6", "#DCE2FA", "list"),
    _s("portal-tenant", "Portal", "Society resident portal", "Dues, complaints, notices",
       "A portal for a housing society: residents sign in to see maintenance dues, raise a complaint, and read notices; the committee sees all complaints.",
       "#FFF8F0", "#40250B", "#C9731B", "#F8E2C8", "board"),
    _s("portal-client", "Portal", "Client document portal", "Upload, status, messages",
       "A portal for an accounting firm: clients sign in, upload documents, see the status of each filing, and message their accountant.",
       "#F4F6F8", "#1B2733", "#3E6B8F", "#DDE5EC", "list"),
    _s("land-launch", "Landing page", "App launch page", "One promise, one button",
       "A landing page for a new mobile app: a clear one-line promise, three benefits with icons, screenshots, and a download button.",
       "#12102B", "#F3F1FF", "#8B6CFF", "#241F52", "hero"),
    _s("land-course", "Landing page", "Course enrolment page", "Syllabus, fees, enrol",
       "A landing page for an online course: what you will learn, the syllabus, the instructor, fees, student reviews, and an enrol button.",
       "#FFFAF0", "#33260A", "#E59E0B", "#FBEBC4", "split"),
    _s("land-event", "Landing page", "Event registration", "Date, speakers, register",
       "A landing page for a one-day event: date and venue, the speakers, the schedule, and a registration form.",
       "#F0FAFF", "#08303F", "#0BA5D6", "#CDEDF8", "form"),
    _s("blog-food", "Blog", "Home cooking blog", "Recipes, photos, search",
       "A blog for home recipes: recipe posts with ingredient lists and steps, categories, search, and a newsletter sign-up.",
       "#FFF7F0", "#3A1A0A", "#E2571E", "#FADFCB", "feed"),
    _s("blog-travel", "Blog", "Travel journal", "Trips, maps, stories",
       "A travel journal blog: long stories with big photos, a page per trip with a route map, and an about page.",
       "#F1F7F4", "#133327", "#2E8B63", "#D3EBE0", "feed"),
    _s("blog-news", "Blog", "Local news and notices", "Posts, categories",
       "A local news blog: latest posts on the front page, categories like civic, sports and culture, and a page for notices.",
       "#F7F7F7", "#1B1B1B", "#D62F2F", "#E4E4E4", "list"),
    _s("tool-inventory", "Internal tool", "Stock register", "Items, in and out, low stock",
       "An internal tool for a warehouse: a list of items with quantity, add stock in and out with a note, and a low-stock warning; staff sign in.",
       "#F5F7F2", "#222B14", "#6E8B1F", "#E1E9CB", "list"),
    _s("tool-requests", "Internal tool", "Staff request tracker", "Raise, approve, track",
       "An internal tool where staff raise requests (leave, purchase, repair), a manager approves or declines, and everyone sees the status.",
       "#F6F5FF", "#221B4D", "#5B47D6", "#E0DCFA", "board"),
    _s("tool-visits", "Internal tool", "Field visit log", "Visits, notes, follow-up",
       "An internal tool for a field team: log each customer visit with notes and a photo, set a follow-up date, and see today's visits.",
       "#F2F8FA", "#10303A", "#1593B5", "#D1EAF1", "form"),
]


def all_() -> dict:
    return {"chips": CHIPS, "starters": STARTERS}
