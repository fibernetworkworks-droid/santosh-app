"""v0.841 L0/L15 STUDIO CARD asks: 30 asks from a one-line brochure to a small SaaS, in the words a shop owner would use.

10 brochure + 8 shop / booking (the Site Engine's ground) + 8 portal / dashboard + 4 SaaS (the App Engine's ground).
`engine` = which Studio engine the ask goes to by default. `must` = words the first screen should show (the business's
own name or trade - checked in code against the rendered text, never judged by a model). `edit` = a small exact change
timed on its own (3 asks): the engine is asked to make it with NO model call (search + exact replace)."""
from __future__ import annotations

_B = "brochure"
_S = "shop"
_P = "portal"
_X = "saas"

ASKS = [
    # ---- 10 brochure
    {"id": "b01", "kind": _B, "engine": "site", "ask": "A website for Sharma Sweets in Akola: menu, Diwali gift boxes, timings and a WhatsApp order button.", "must": ["Sharma Sweets"],
     "edit": {"search": "Diwali", "replace": "Dussehra"}},
    {"id": "b02", "kind": _B, "engine": "site", "ask": "A website for Dr. Patil's family clinic in Pune: doctors, timings, location and a call button.", "must": ["Patil"]},
    {"id": "b03", "kind": _B, "engine": "site", "ask": "A website for Glow Beauty Salon in Nagpur with services, prices and photos of our work.", "must": ["Glow"]},
    {"id": "b04", "kind": _B, "engine": "site", "ask": "A portfolio website for wedding photographer Rohan Deshmukh: gallery, packages, contact form.", "must": ["Rohan"]},
    {"id": "b05", "kind": _B, "engine": "site", "ask": "A website for Kulkarni & Associates, a chartered accountant firm in Indore: services, team, contact.", "must": ["Kulkarni"]},
    {"id": "b06", "kind": _B, "engine": "site", "ask": "A website for IronWorks Gym in Jaipur: plans and fees, trainers, timings, free trial form.", "must": ["IronWorks"]},
    {"id": "b07", "kind": _B, "engine": "site", "ask": "A website for Saraswati Vidya Mandir, a school in Lucknow: admissions, fees, notices, contact.", "must": ["Saraswati"]},
    {"id": "b08", "kind": _B, "engine": "site", "ask": "A website for Spice Route Restaurant in Surat: menu with photos, table booking and directions.", "must": ["Spice Route"]},
    {"id": "b09", "kind": _B, "engine": "site", "ask": "A website for Asha Foundation, an NGO in Nashik: our mission, projects, volunteer and donate pages.", "must": ["Asha"]},
    {"id": "b10", "kind": _B, "engine": "site", "ask": "A website for Mehta Interiors in Bhopal: projects gallery, services, how we work, contact.", "must": ["Mehta"]},
    # ---- 8 shop / booking
    {"id": "s01", "kind": _S, "engine": "site", "ask": "An online store for Rani Sarees in Surat: catalogue, cart, UPI and cash on delivery, GST invoice.", "must": ["Rani"],
     "edit": {"search": "Surat", "replace": "Nagpur"}},
    {"id": "s02", "kind": _S, "engine": "site", "ask": "An online grocery for FreshBasket in Pune with delivery slots and cash on delivery.", "must": ["FreshBasket"]},
    {"id": "s03", "kind": _S, "engine": "site", "ask": "An online bookshop for Page One Books in Nagpur with search and courier delivery.", "must": ["Page One"]},
    {"id": "s04", "kind": _S, "engine": "site", "ask": "A booking site for Lotus Salon: choose a service and a time slot, the owner confirms.", "must": ["Lotus"]},
    {"id": "s05", "kind": _S, "engine": "site", "ask": "A booking site for ActiveLife Physio clinic: pick a treatment, see free slots, book with name and phone.", "must": ["ActiveLife"]},
    {"id": "s06", "kind": _S, "engine": "site", "ask": "A booking site for GreenField Turf: hourly slots by day, peak and off-peak prices.", "must": ["GreenField"]},
    {"id": "s07", "kind": _S, "engine": "site", "ask": "A booking site for a maths home-tutor, Mr. Verma: demo class request and monthly batches.", "must": ["Verma"]},
    {"id": "s08", "kind": _S, "engine": "site", "ask": "A booking site for QuickFix mobile repair: book a pickup, price list, repair status check.", "must": ["QuickFix"]},
    # ---- 8 portal / dashboard
    {"id": "p01", "kind": _P, "engine": "app", "ask": "A student and parent portal for Bright Coaching: sign in, see attendance, test marks and fee status, read notices.", "must": ["Bright"]},
    {"id": "p02", "kind": _P, "engine": "app", "ask": "A resident portal for Sunrise Society: maintenance dues, raise a complaint, read notices; the committee sees all complaints.", "must": ["Sunrise"]},
    {"id": "p03", "kind": _P, "engine": "app", "ask": "A client portal for Kulkarni & Associates: clients upload documents, see filing status, message their accountant.", "must": ["Kulkarni"]},
    {"id": "p04", "kind": _P, "engine": "app", "ask": "A sales dashboard for a shop owner: this week against last week, a line chart by day, best sellers, low stock.", "must": ["Sales"],
     "edit": {"search": "Sales", "replace": "Revenue"}},
    {"id": "p05", "kind": _P, "engine": "app", "ask": "A fee tracker for a school office: fees collected this month, students with dues, a reminder button per family.", "must": ["Fee"]},
    {"id": "p06", "kind": _P, "engine": "app", "ask": "A leads dashboard: new enquiries by source, their status from new to won, and the follow-ups due today.", "must": ["Lead"]},
    {"id": "p07", "kind": _P, "engine": "app", "ask": "A dispatch dashboard for a delivery business: staff add jobs, the dispatcher assigns a driver and marks delivered, live counts.", "must": ["Dispatch"]},
    {"id": "p08", "kind": _P, "engine": "app", "ask": "A staff request tracker: raise leave or purchase requests, a manager approves or declines, everyone sees the status.", "must": ["Request"]},
    # ---- 4 SaaS
    {"id": "x01", "kind": _X, "engine": "app", "ask": "A small invoicing tool for freelancers: customers, invoices with GST, status paid or unpaid, a monthly total.", "must": ["Invoice"]},
    {"id": "x02", "kind": _X, "engine": "app", "ask": "An appointment scheduler for a clinic group: doctors, slots, patients, a daily agenda for each doctor.", "must": ["Appointment"]},
    {"id": "x03", "kind": _X, "engine": "app", "ask": "An inventory tool for a warehouse: items, stock in and out with a note, low-stock warning; staff sign in.", "must": ["Inventory"]},
    {"id": "x04", "kind": _X, "engine": "app", "ask": "A helpdesk for a small company: customers raise tickets, agents reply and close them, a count of open tickets.", "must": ["Ticket"]},
]
