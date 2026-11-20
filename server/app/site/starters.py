"""v0.835 GHAR + SHURUAAT (L12 of docs/LOVABLE_STUDIO_PLAN.md): the Studio home's starting points.

24 hand-checked STARTERS, three for each of the eight home chips (Website, Online store, Web app, Portfolio, Event,
Community, Course, Tool or game - O1: not only business sites). A starter is a complete, specific ask (what the page is, who uses it, what it must do)
plus its own palette and layout. The Studio draws each one's thumbnail from THAT palette and layout (SVG, no image file),
so the card shows the look the ask will be built in. They are NOT already-built sites: choosing one puts its ask in the
box (she can change every word) and the normal Build runs. The 1,00,000 generated template prompts stay as "Ideas"."""
from __future__ import annotations

CHIPS = ["Website", "Online store", "Web app", "Portfolio", "Event", "Community", "Course", "Tool or game"]
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
    _s("book-salon", "Website", "Salon appointments", "Services, prices, slots",
       "A booking site for a salon: services with prices, pick a stylist and a time slot, and a confirmation the owner approves.",
       "#FFF5FA", "#431030", "#C2338A", "#F8D8EA", "form"),
    _s("shop-saree", "Online store", "Saree boutique", "Catalogue, cart, UPI and COD",
       "An online store for a saree boutique: product pages with several photos, sizes and colours, a cart, UPI and cash-on-delivery checkout, and GST invoices.",
       "#FFF4F6", "#4A1424", "#B8264F", "#F9D9E1", "grid"),
    _s("shop-grocery", "Online store", "Local grocery delivery", "Daily items, slots, WhatsApp",
       "An online store for a local grocery: categories, weights and prices, a cart with a delivery-slot picker, and cash on delivery.",
       "#F4FAEC", "#1E3A0F", "#4E9A1E", "#DDEFC6", "list"),
    _s("shop-books", "Online store", "Independent bookshop", "Shelves, search, orders",
       "An online store for an independent bookshop: search by title and author, staff picks, a cart, and pickup or courier delivery.",
       "#FBF7F0", "#2B2118", "#8A5A2B", "#EADFCB", "split"),
    _s("dash-sales", "Web app", "Weekly sales", "Numbers, trend, best sellers",
       "A dashboard for a shop owner: this week's sales against last week, a line chart by day, best-selling items, and low stock warnings.",
       "#F6F8FC", "#14213D", "#2F6BFF", "#DCE6FB", "chart"),
    _s("portal-student", "Web app", "Student and parent portal", "Marks, fees, notices",
       "A portal for a coaching class: students and parents sign in, see attendance, test marks and fee status, and read notices from teachers.",
       "#F5F7FF", "#1A2250", "#3D55D6", "#DCE2FA", "list"),
    _s("tool-requests", "Web app", "Staff request tracker", "Raise, approve, track",
       "An internal tool where staff raise requests (leave, purchase, repair), a manager approves or declines, and everyone sees the status.",
       "#F6F5FF", "#221B4D", "#5B47D6", "#E0DCFA", "board"),
    _s("web-studio", "Portfolio", "Photographer's portfolio", "Work, about, contact",
       "A portfolio website for a wedding photographer: a full-screen gallery of recent work, a short about page, packages, and a contact form.",
       "#111111", "#F5F5F5", "#E8B34A", "#222222", "grid"),
    _s("port-dev", "Portfolio", "Developer's portfolio", "Projects, skills, contact",
       "A personal portfolio for a software developer: a short intro, selected projects with screenshots and links, skills, a downloadable CV, and a contact form. Clean and quiet.",
       "#0E1116", "#E8EDF2", "#4FB3FF", "#1A2029", "grid"),
    _s("port-art", "Portfolio", "Illustrator's portfolio", "Artwork, commissions, shop",
       "A portfolio for an illustrator: a big gallery of artwork by series, a page on how commissions work with prices, an about page, and an enquiry form. Playful and colourful.",
       "#FFF8EE", "#2A1B12", "#E4572E", "#FCE3CF", "grid"),
    _s("event-wedding", "Event", "Wedding website", "Our story, events, RSVP",
       "A wedding website for a couple: our story with photos, the haldi, mehendi, wedding and reception with dates, venues and maps, travel and stay notes, and an RSVP form for guests.",
       "#FFF7F2", "#3E1A16", "#B5473A", "#F8DDD5", "hero"),
    _s("land-event", "Event", "Event registration", "Date, speakers, register",
       "A landing page for a one-day event: date and venue, the speakers, the schedule, and a registration form.",
       "#F0FAFF", "#08303F", "#0BA5D6", "#CDEDF8", "form"),
    _s("event-bday", "Event", "Birthday party page", "Invite, venue, who is coming",
       "A party page for a 30th birthday: a fun invite with the date, time and venue map, the dress code, a photo wall after the party, and a simple form to say who is coming.",
       "#FFF4FB", "#3A1036", "#D6338F", "#FAD6EC", "split"),
    _s("comm-ngo", "Community", "Charity cause page", "Our work, impact, volunteer",
       "A website for a small charity that teaches children: our work with photos, impact numbers, stories, how to volunteer, and how to donate (the donate button opens their own UPI details).",
       "#F3FAF4", "#123020", "#2F8F4E", "#D5EEDC", "split"),
    _s("comm-club", "Community", "Running club", "Runs, members, join",
       "A website for a weekend running club: upcoming runs with meeting points on a map, a leaderboard of members' kilometres, photos from past runs, and a join form.",
       "#F2F7FF", "#0F2440", "#2563EB", "#D7E4FB", "list"),
    _s("blog-news", "Community", "Local news and notices", "Posts, categories",
       "A local news blog: latest posts on the front page, categories like civic, sports and culture, and a page for notices.",
       "#F7F7F7", "#1B1B1B", "#D62F2F", "#E4E4E4", "list"),
    _s("land-course", "Course", "Course enrolment page", "Syllabus, fees, enrol",
       "A landing page for an online course: what you will learn, the syllabus, the instructor, fees, student reviews, and an enrol button.",
       "#FFFAF0", "#33260A", "#E59E0B", "#FBEBC4", "split"),
    _s("course-lessons", "Course", "Free lessons with quizzes", "Lessons, practice, progress",
       "A learning site for class 10 maths: chapters with short lessons, worked examples, a quick quiz after each lesson that marks answers on the page, and a progress tracker kept on the device.",
       "#F7F5FF", "#1E1650", "#5B3FD6", "#E2DCFB", "list"),
    _s("course-notes", "Course", "Study notes hub", "Notes, search, downloads",
       "A study notes website for engineering students: subjects and topics, clear notes with diagrams, search, and printable PDF downloads of each topic.",
       "#FAFAF7", "#1F2421", "#3D7A5B", "#E3EBE5", "feed"),
    _s("tool-emi", "Tool or game", "EMI calculator", "Loan, rate, months, answer",
       "A loan EMI calculator page: sliders for loan amount, interest rate and months, the monthly EMI worked out as you move them, a chart of interest versus principal, and a month-by-month table.",
       "#F4F8FB", "#11283A", "#0E7BC4", "#D6E7F3", "chart"),
    _s("game-quiz", "Tool or game", "General knowledge quiz", "Questions, timer, score",
       "A quiz game page: ten general knowledge questions with four choices each, a 20-second timer per question, a score at the end with the right answers, and a play again button. Works on phone and keyboard.",
       "#14102E", "#F2EFFF", "#FFB648", "#2A2356", "board"),
    _s("game-arcade", "Tool or game", "Small arcade game", "Play, score, best score",
       "A small arcade game on one page: a kite flying between buildings that you keep up with a tap or the space bar, a rising score, a best score, and a restart button. Bright and simple.",
       "#E9F6FF", "#0B2A44", "#FF6A3D", "#CDE9FB", "hero"),
]


def all_() -> dict:
    return {"chips": CHIPS, "starters": STARTERS}
