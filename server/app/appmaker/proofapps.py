"""v0.771 PROOF APPS - the App plan's own gate, run on the server.

`docs/COMPLEX_APPS_PLAN.md` ends every pillar on "a proof app" and none existed: twelve pillars (A-L) were built and
tested piece by piece, but no complete app had ever gone through the whole road. This module is that road for the
plan's five proof apps (school ERP, clinic, food delivery, marketplace, field-service CRM):

    one line -> a naksha (written here by hand, so no model call and the same result every run)
             -> Pillar K's checker (the plan cannot promise what Hoola cannot build)
             -> module by module: approve, build through the REAL engines, prove the module's stories (Pillar J)
             -> the app's brain (formulas, rules, unique, workflows, functions) applied through the real logic engine
             -> hand-written scenario tests on a throwaway twin, every privacy step a "must be refused"

Everything runs on a hidden tenant (`__proofapps__`), never on her apps, and each run starts from fresh projects.
Applying the brain here is the harness's own act on its own test app - on her app that stays HER tap.

What this does NOT prove, and the card says so every time: nothing here ran on a real phone (the plan's gate asks
for that), the rider / vendor apps of the family are not built (they need a design + a native build), and every
part that needs her credential (payment keys, Firebase, a connector account) is a named next step, not a pass.

`python -m app.appmaker.proofapps` prints the card; `--only clinic` runs one.
"""
from __future__ import annotations

import json
import logging
import secrets
import sys
import time
from typing import Any

from ..db import now, session
from .models import AppProject

log = logging.getLogger("santosh.proofapps")

TENANT = "__proofapps__"
TAG = "proof_app"

ADMIN = {"create": "admin", "read": "admin", "update": "admin", "delete": "admin"}
MINE = {"create": "member", "read": "own", "update": "admin", "delete": "admin"}


def _f(key: str, typ: str = "text", required: bool = False, **kw: Any) -> dict[str, Any]:
    return {"key": key, "label": key.replace("_", " ").title(), "type": typ, **({"required": True} if required else {}), **kw}


# ---------------------------------------------------------------- the five apps of the plan
# Each is {key, label, line, spec (a Pillar K naksha), scenarios (Pillar J), not_proved (said on the card)}.
SCHOOL = {
    "key": "school_erp", "label": "School ERP",
    "line": "Saraswati Vidyalaya: parents apply for leave, the office keeps fees, teachers approve",
    "spec": {
        "one_line": "Saraswati Vidyalaya ki app: chhutti ki arzi, fees ka hisaab, notice",
        "user_types": [{"key": "parent", "label": "Parent", "role": "member", "app": "main"},
                       {"key": "teacher", "label": "Teacher", "role": "staff", "app": "main"},
                       {"key": "principal", "label": "Principal", "role": "admin", "app": "main"}],
        "modules": [
            {"key": "leave", "label": "Chhutti ki arzi", "why": "Parent apne bachche ki chhutti maange, teacher maane",
             "parts": {"lists": [{"key": "leave_requests", "label": "Leave requests", "rules": MINE,
                                  "fields": [_f("student", required=True), _f("from_date", "date", True),
                                             _f("reason", "long_text"),
                                             _f("status", "choice", options=["Pending", "Approved", "Rejected"])]}],
                       "stories": [{"as": "parent", "want": "bachche ki chhutti maangun", "so_that": "school ko pata ho"}]}},
            {"key": "fees", "label": "Fees", "why": "Office har bachche ki fees aur baaki rakam rakhe", "needs": ["leave"],
             "parts": {"lists": [{"key": "fees", "label": "Fees", "rules": ADMIN,
                                  "fields": [_f("student", required=True), _f("amount", "number", True),
                                             _f("paid", "number"), _f("due", "number")]}],
                       "logic": {"workflows": [{"coll": "leave_requests", "field": "status",
                                                "states": ["Pending", "Approved", "Rejected"], "initial": "Pending",
                                                "transitions": [
                                                    {"from": ["Pending"], "to": "Approved", "label": "Approve", "who": ["staff"]},
                                                    {"from": ["Pending"], "to": "Rejected", "label": "Reject", "who": ["staff"]}]}],
                                 "formulas": [{"coll": "fees", "field": "due", "expr": "amount - paid"}],
                                 "rules": [{"coll": "fees", "check": "amount > 0", "message": "Fees 0 se zyada honi chahiye"},
                                           {"coll": "fees", "check": "paid <= amount", "message": "Jama fees se zyada nahi"}]},
                       "stories": [{"as": "staff", "want": "fees likhun", "so_that": "baaki rakam dikhe"}]}},
            {"key": "notices", "label": "Notice board", "why": "School sab parents ko notice de",
             "parts": {"lists": [{"key": "notices", "label": "Notices",
                                  "rules": {"create": "admin", "read": "members", "update": "admin", "delete": "admin"},
                                  "fields": [_f("title", required=True), _f("body", "long_text")]}],
                       "push": True}},
        ],
        "release": [{"phase": "Pehle", "modules": ["leave", "fees"], "why": "roz ka kaam"}],
    },
    "scenarios": [
        {"story": "A parent applies for leave and it starts as Pending",
         "steps": [{"do": "signup", "who": "parent1"},
                   {"do": "create", "who": "parent1", "list": "leave_requests",
                    "data": {"student": "Aarav Patil", "from_date": "2026-11-20", "reason": "Shaadi"}, "save": "l1"},
                   {"do": "open", "who": "parent1", "row": "l1", "expect": {"status": "Pending"}}]},
        {"story": "Another parent cannot see someone else's leave request",
         "steps": [{"do": "signup", "who": "parent1"},
                   {"do": "create", "who": "parent1", "list": "leave_requests",
                    "data": {"student": "Aarav Patil", "from_date": "2026-11-20"}, "save": "l1"},
                   {"do": "signup", "who": "parent2"},
                   {"do": "open", "who": "parent2", "row": "l1", "must": "refused"},
                   {"do": "read", "who": "parent2", "list": "leave_requests", "expect_count": 0}]},
        {"story": "A teacher approves; a parent cannot approve their own leave",
         "steps": [{"do": "signup", "who": "parent1"},
                   {"do": "create", "who": "parent1", "list": "leave_requests",
                    "data": {"student": "Aarav Patil", "from_date": "2026-11-20"}, "save": "l1"},
                   {"do": "set", "who": "parent1", "row": "l1", "data": {"status": "Approved"}, "must": "refused"},
                   {"do": "signup", "who": "teacher1", "role": "staff"},
                   {"do": "set", "who": "teacher1", "row": "l1", "data": {"status": "Approved"}},
                   {"do": "open", "who": "parent1", "row": "l1", "expect": {"status": "Approved"}}]},
        {"story": "The office's fee rows work out what is still due, and refuse nonsense",
         "steps": [{"do": "signup", "who": "office1", "role": "staff"},
                   {"do": "create", "who": "office1", "list": "fees",
                    "data": {"student": "Aarav Patil", "amount": 12000, "paid": 5000}, "save": "f1"},
                   {"do": "open", "who": "office1", "row": "f1", "expect": {"due": 7000}},
                   {"do": "create", "who": "office1", "list": "fees",
                    "data": {"student": "Diya Patil", "amount": 0}, "must": "refused"},
                   {"do": "create", "who": "office1", "list": "fees",
                    "data": {"student": "Diya Patil", "amount": 1000, "paid": 2000}, "must": "refused"}]},
        {"story": "A parent cannot read the fee register or post a notice, but reads notices",
         "steps": [{"do": "signup", "who": "office1", "role": "staff"},
                   {"do": "create", "who": "office1", "list": "notices", "data": {"title": "Diwali chhutti"}},
                   {"do": "signup", "who": "parent1"},
                   {"do": "read", "who": "parent1", "list": "fees", "must": "refused"},
                   {"do": "create", "who": "parent1", "list": "notices", "data": {"title": "Fake"}, "must": "refused"},
                   {"do": "read", "who": "parent1", "list": "notices", "expect_count": 1}]},
    ],
    "not_proved": ["a parent seeing HER OWN child's fee row (rows belong to whoever wrote them - the office - so this "
                   "needs a gate / pass list, not built in this proof)", "report cards as PDFs"],
}

CLINIC = {
    "key": "clinic", "label": "Clinic",
    "line": "Dr. Kulkarni's clinic: patients book a slot, one slot cannot be booked twice, the desk checks them in",
    "spec": {
        "one_line": "Kulkarni Clinic ki app: appointment, ek slot ek patient, check-in",
        "user_types": [{"key": "patient", "label": "Patient", "role": "member", "app": "main"},
                       {"key": "desk", "label": "Reception", "role": "staff", "app": "main"}],
        "modules": [
            {"key": "appointments", "label": "Appointment", "why": "Patient slot book kare, doosra wahi slot na le",
             "parts": {"lists": [{"key": "appointments", "label": "Appointments", "rules": MINE,
                                  "fields": [_f("patient_name", required=True),
                                             _f("phone", "phone", True, private=True),
                                             _f("doctor", "choice", True, options=["Dr. Kulkarni", "Dr. Joshi"]),
                                             _f("slot", required=True), _f("problem", "long_text"),
                                             _f("status", "choice", options=["Booked", "Checked in", "Done", "Cancelled"])]}],
                       "logic": {"unique": [{"coll": "appointments", "fields": ["doctor", "slot"],
                                             "message": "Yeh slot pehle se book hai"}],
                                 "workflows": [{"coll": "appointments", "field": "status",
                                                "states": ["Booked", "Checked in", "Done", "Cancelled"], "initial": "Booked",
                                                "transitions": [
                                                    {"from": ["Booked"], "to": "Checked in", "label": "Check in", "who": ["staff"]},
                                                    {"from": ["Checked in"], "to": "Done", "label": "Done", "who": ["staff"]},
                                                    {"from": "*", "to": "Cancelled", "label": "Cancel", "who": ["staff"]}]}]},
                       "push": True,
                       "stories": [{"as": "patient", "want": "doctor ka slot book karun", "so_that": "line na lage"}]}},
        ],
    },
    "scenarios": [
        {"story": "A patient books a slot; another patient cannot see it",
         "steps": [{"do": "signup", "who": "pat1"},
                   {"do": "create", "who": "pat1", "list": "appointments",
                    "data": {"patient_name": "Sunita Rao", "phone": "9876500011", "doctor": "Dr. Kulkarni",
                             "slot": "2026-11-20 10:00"}, "save": "a1"},
                   {"do": "open", "who": "pat1", "row": "a1", "expect": {"status": "Booked"}},
                   {"do": "signup", "who": "pat2"},
                   {"do": "open", "who": "pat2", "row": "a1", "must": "refused"}]},
        {"story": "The same doctor's slot cannot be booked twice; another doctor at that time can",
         "steps": [{"do": "signup", "who": "pat1"},
                   {"do": "create", "who": "pat1", "list": "appointments",
                    "data": {"patient_name": "Sunita Rao", "phone": "9876500011", "doctor": "Dr. Kulkarni",
                             "slot": "2026-11-20 11:00"}},
                   {"do": "signup", "who": "pat2"},
                   {"do": "create", "who": "pat2", "list": "appointments",
                    "data": {"patient_name": "Ravi Shah", "phone": "9876500012", "doctor": "Dr. Kulkarni",
                             "slot": "2026-11-20 11:00"}, "must": "refused"},
                   {"do": "create", "who": "pat2", "list": "appointments",
                    "data": {"patient_name": "Ravi Shah", "phone": "9876500012", "doctor": "Dr. Joshi",
                             "slot": "2026-11-20 11:00"}}]},
        {"story": "The desk checks a patient in and then marks done, in that order; the patient rates the visit",
         "steps": [{"do": "signup", "who": "pat1"},
                   {"do": "create", "who": "pat1", "list": "appointments",
                    "data": {"patient_name": "Sunita Rao", "phone": "9876500011", "doctor": "Dr. Kulkarni",
                             "slot": "2026-11-21 11:00"}, "save": "a1"},
                   {"do": "signup", "who": "desk1", "role": "staff"},
                   {"do": "set", "who": "desk1", "row": "a1", "data": {"status": "Done"}, "must": "refused"},
                   {"do": "set", "who": "desk1", "row": "a1", "data": {"status": "Checked in"}},
                   {"do": "set", "who": "desk1", "row": "a1", "data": {"status": "Done"}},
                   {"do": "rate", "who": "pat1", "row": "a1", "stars": 5}]},
        {"story": "A patient cannot check themself in",
         "steps": [{"do": "signup", "who": "pat1"},
                   {"do": "create", "who": "pat1", "list": "appointments",
                    "data": {"patient_name": "Sunita Rao", "phone": "9876500011", "doctor": "Dr. Joshi",
                             "slot": "2026-11-22 12:00"}, "save": "a1"},
                   {"do": "set", "who": "pat1", "row": "a1", "data": {"status": "Checked in"}, "must": "refused"}]},
    ],
    "not_proved": ["prescriptions as PDFs to the patient (a row the doctor writes belongs to the doctor - needs a gate)",
                   "the live queue board (v0.459) - a website feature, not part of this app proof"],
}

FOOD = {
    "key": "food_delivery", "label": "Food delivery",
    "line": "Annapurna Tiffins: customers order thalis, the kitchen prices them (never the phone), riders deliver",
    "spec": {
        "one_line": "Annapurna Tiffins ki app: order, kitchen, delivery",
        "user_types": [{"key": "customer", "label": "Customer", "role": "member", "app": "main"},
                       {"key": "kitchen", "label": "Kitchen", "role": "staff", "app": "main"},
                       {"key": "rider", "label": "Rider", "role": "staff", "app": "rider"}],
        "modules": [
            {"key": "menu", "label": "Menu", "why": "Sab ko menu dikhe",
             "parts": {"lists": [{"key": "menu", "label": "Menu",
                                  "rules": {"create": "admin", "read": "public", "update": "admin", "delete": "admin"},
                                  "fields": [_f("dish", required=True), _f("price", "number", True)]}]}},
            {"key": "ordering", "label": "Order", "why": "Customer order de, daam kitchen ke hisaab se", "needs": ["menu"],
             "parts": {"lists": [{"key": "food_orders", "label": "Orders", "rules": MINE,
                                  "fields": [_f("item", "choice", True, options=["Thali", "Biryani", "Dosa"]),
                                             _f("qty", "number", True), _f("amount", "number"),
                                             _f("address", "long_text", True),
                                             _f("status", "choice",
                                                options=["Placed", "Cooking", "Out for delivery", "Delivered"])]}],
                       "logic": {"functions": [{"name": "rate_of", "label": "Rate", "params": ["item"],
                                                "body": "if item == \"Thali\" { return 150 }\n"
                                                        "if item == \"Biryani\" { return 220 }\n"
                                                        "if item == \"Dosa\" { return 90 }\nreturn 0",
                                                "tests": [{"args": ["Thali"], "expect": 150},
                                                          {"args": ["Dosa"], "expect": 90}]}],
                                 "formulas": [{"coll": "food_orders", "field": "amount", "expr": "qty * rate_of(item)"}],
                                 "rules": [{"coll": "food_orders", "check": "qty > 0", "message": "Kam se kam 1"},
                                           {"coll": "food_orders", "check": "qty <= 20", "message": "Ek baar mein 20 tak"}],
                                 "workflows": [{"coll": "food_orders", "field": "status",
                                                "states": ["Placed", "Cooking", "Out for delivery", "Delivered"],
                                                "initial": "Placed",
                                                "transitions": [
                                                    {"from": ["Placed"], "to": "Cooking", "label": "Cook", "who": ["staff"]},
                                                    {"from": ["Cooking"], "to": "Out for delivery", "label": "Send", "who": ["staff"]},
                                                    {"from": ["Out for delivery"], "to": "Delivered", "label": "Delivered",
                                                     "who": ["staff"]}]}]},
                       "pay": {"what": "UPI / card payment on the order"}, "track": True, "push": True,
                       "stories": [{"as": "customer", "want": "thali order karun", "so_that": "ghar pe khana aaye"}]}},
        ],
    },
    "scenarios": [
        {"story": "The phone never prices: the server works the amount out from the item",
         "steps": [{"do": "signup", "who": "cust1"},
                   {"do": "create", "who": "cust1", "list": "food_orders",
                    "data": {"item": "Thali", "qty": 2, "amount": 1, "address": "Flat 4, Shivaji Nagar"}, "save": "o1"},
                   {"do": "open", "who": "cust1", "row": "o1", "expect": {"amount": 300, "status": "Placed"}}]},
        {"story": "Zero or 50 thalis are refused",
         "steps": [{"do": "signup", "who": "cust1"},
                   {"do": "create", "who": "cust1", "list": "food_orders",
                    "data": {"item": "Thali", "qty": 0, "address": "Flat 4"}, "must": "refused"},
                   {"do": "create", "who": "cust1", "list": "food_orders",
                    "data": {"item": "Thali", "qty": 50, "address": "Flat 4"}, "must": "refused"}]},
        {"story": "Another customer cannot see my order; the kitchen moves it in order; I rate it after delivery",
         "steps": [{"do": "signup", "who": "cust1"},
                   {"do": "create", "who": "cust1", "list": "food_orders",
                    "data": {"item": "Dosa", "qty": 3, "address": "Flat 4"}, "save": "o1"},
                   {"do": "signup", "who": "cust2"},
                   {"do": "open", "who": "cust2", "row": "o1", "must": "refused"},
                   {"do": "rate", "who": "cust1", "row": "o1", "stars": 4, "must": "refused"},
                   {"do": "signup", "who": "kitchen1", "role": "staff"},
                   {"do": "set", "who": "kitchen1", "row": "o1", "data": {"status": "Delivered"}, "must": "refused"},
                   {"do": "set", "who": "kitchen1", "row": "o1", "data": {"status": "Cooking"}},
                   {"do": "set", "who": "kitchen1", "row": "o1", "data": {"status": "Out for delivery"}},
                   {"do": "set", "who": "kitchen1", "row": "o1", "data": {"status": "Delivered"}},
                   {"do": "rate", "who": "cust1", "row": "o1", "stars": 4},
                   {"do": "rate", "who": "cust2", "row": "o1", "stars": 1, "must": "refused"}]},
        {"story": "Anyone can read the menu; only the kitchen can change it",
         "steps": [{"do": "signup", "who": "kitchen1", "role": "staff"},
                   {"do": "create", "who": "kitchen1", "list": "menu", "data": {"dish": "Thali", "price": 150}, "save": "m1"},
                   {"do": "signup", "who": "cust1"},
                   {"do": "read", "who": "cust1", "list": "menu", "expect_count": 1},
                   {"do": "set", "who": "cust1", "row": "m1", "data": {"price": 1}, "must": "refused"}]},
    ],
    "not_proved": ["the rider app (a second app on the same data - needs its own design + build)",
                   "online payment (her gateway keys)", "live rider tracking (her switch + a real phone)",
                   "the price list lives in the brain's rate_of function, not read from the Menu list"],
}

MARKET = {
    "key": "marketplace", "label": "Multi-vendor marketplace",
    "line": "Haath Ka Bana: artisans list their own products, the platform keeps 10% and pays the rest",
    "spec": {
        "one_line": "Haath Ka Bana marketplace: vendors, listings, commission",
        "user_types": [{"key": "vendor", "label": "Vendor", "role": "member", "app": "main"},
                       {"key": "buyer", "label": "Buyer", "role": "member", "app": "main"},
                       {"key": "ops", "label": "Platform team", "role": "staff", "app": "main"}],
        "modules": [
            {"key": "listings", "label": "Listings", "why": "Har vendor apne product khud daale, koi aur na badle",
             "parts": {"lists": [{"key": "listings", "label": "Listings",
                                  "rules": {"create": "member", "read": "public", "update": "own", "delete": "own"},
                                  "fields": [_f("title", required=True), _f("price", "number", True),
                                             _f("stock", "number")]}],
                       "stories": [{"as": "vendor", "want": "apna product daalun", "so_that": "log khareeden"}]}},
            {"key": "settlements", "label": "Hisaab", "why": "Har sale par 10% platform, baaki vendor ka", "needs": ["listings"],
             "parts": {"lists": [{"key": "sales", "label": "Sales", "rules": ADMIN,
                                  "fields": [_f("vendor", required=True), _f("amount", "number", True),
                                             _f("commission", "number"), _f("payout", "number")]}],
                       "logic": {"formulas": [{"coll": "sales", "field": "commission", "expr": "round(amount * 0.1, 2)"},
                                              {"coll": "sales", "field": "payout", "expr": "amount - commission"}],
                                 "rules": [{"coll": "sales", "check": "amount > 0", "message": "Sale 0 se zyada"},
                                           {"coll": "listings", "check": "price > 0", "message": "Daam 0 se zyada"}]},
                       "pay": {"what": "split payouts to vendors through her gateway's own route product"}}},
        ],
    },
    "scenarios": [
        {"story": "A vendor lists a product; everyone, even signed out, can see it",
         "steps": [{"do": "signup", "who": "vend1"},
                   {"do": "create", "who": "vend1", "list": "listings",
                    "data": {"title": "Warli painting", "price": 1800, "stock": 3}, "save": "p1"},
                   {"do": "signup", "who": "buyer1"},
                   {"do": "read", "who": "buyer1", "list": "listings", "expect_count": 1}]},
        {"story": "Another vendor cannot change or delete my listing; I can",
         "steps": [{"do": "signup", "who": "vend1"},
                   {"do": "create", "who": "vend1", "list": "listings",
                    "data": {"title": "Warli painting", "price": 1800}, "save": "p1"},
                   {"do": "signup", "who": "vend2"},
                   {"do": "set", "who": "vend2", "row": "p1", "data": {"price": 10}, "must": "refused"},
                   {"do": "set", "who": "vend1", "row": "p1", "data": {"price": 1700}},
                   {"do": "open", "who": "vend1", "row": "p1", "expect": {"price": 1700}}]},
        {"story": "A free listing is refused",
         "steps": [{"do": "signup", "who": "vend1"},
                   {"do": "create", "who": "vend1", "list": "listings",
                    "data": {"title": "Free?", "price": 0}, "must": "refused"}]},
        {"story": "The platform's sale row splits 10% commission and the vendor's payout; vendors cannot read it",
         "steps": [{"do": "signup", "who": "ops1", "role": "staff"},
                   {"do": "create", "who": "ops1", "list": "sales",
                    "data": {"vendor": "vend1", "amount": 1800}, "save": "s1"},
                   {"do": "open", "who": "ops1", "row": "s1", "expect": {"commission": 180, "payout": 1620}},
                   {"do": "signup", "who": "vend1"},
                   {"do": "read", "who": "vend1", "list": "sales", "must": "refused"}]},
    ],
    "not_proved": ["real money split to vendors (her gateway's route product + her keys; money never moves here)",
                   "a vendor seeing HER OWN sales rows (written by the platform - needs a gate)",
                   "courier connector (her Shiprocket account)"],
}

FIELD = {
    "key": "field_service", "label": "Field-service CRM",
    "line": "CoolCare AC service: customers raise a request, the office gives it to a technician, notes are required to close",
    "spec": {
        "one_line": "CoolCare AC service ki app: request, technician, visit",
        "user_types": [{"key": "customer", "label": "Customer", "role": "member", "app": "main"},
                       {"key": "tech", "label": "Technician", "role": "staff", "app": "main"},
                       {"key": "office", "label": "Office", "role": "admin", "app": "main"}],
        "modules": [
            {"key": "requests", "label": "Service request", "why": "Customer AC kharab hone par request daale",
             "parts": {"lists": [{"key": "service_requests", "label": "Service requests", "rules": MINE,
                                  "fields": [_f("name", required=True), _f("phone", "phone", True, private=True),
                                             _f("address", "long_text", True), _f("problem", "long_text", True),
                                             _f("visit_notes", "long_text"), _f("site_photo", "photo"),
                                             _f("signature", "signature"),
                                             _f("status", "choice", options=["Open", "On site", "Done"])]}],
                       "logic": {"workflows": [{"coll": "service_requests", "field": "status",
                                                "states": ["Open", "On site", "Done"], "initial": "Open",
                                                "transitions": [
                                                    {"from": ["Open"], "to": "On site", "label": "Reached", "who": ["staff"]},
                                                    {"from": ["On site"], "to": "Done", "label": "Finish", "who": ["staff"],
                                                     "require": ["visit_notes"]}],
                                                "sla": [{"state": "Open", "hours": 24, "notify": "admins",
                                                         "move_to": "", "message": "Request 24 ghante se khuli hai"}]}]},
                       "push": True,
                       "stories": [{"as": "customer", "want": "AC repair ki request daalun", "so_that": "koi aaye"}]}},
        ],
    },
    "scenarios": [
        {"story": "A customer raises a request; another customer cannot see it or the phone number",
         "steps": [{"do": "signup", "who": "cust1"},
                   {"do": "create", "who": "cust1", "list": "service_requests",
                    "data": {"name": "Meena Desai", "phone": "9876500031", "address": "Baner, Pune",
                             "problem": "AC thanda nahi kar raha"}, "save": "r1"},
                   {"do": "open", "who": "cust1", "row": "r1", "expect": {"status": "Open"}},
                   {"do": "signup", "who": "cust2"},
                   {"do": "open", "who": "cust2", "row": "r1", "must": "refused"}]},
        {"story": "The office gives the job to a technician; a technician cannot take a job given to someone else",
         "steps": [{"do": "signup", "who": "cust1"},
                   {"do": "create", "who": "cust1", "list": "service_requests",
                    "data": {"name": "Meena Desai", "phone": "9876500031", "address": "Baner",
                             "problem": "Gas leak"}, "save": "r1"},
                   {"do": "signup", "who": "office1", "role": "admin"},
                   {"do": "signup", "who": "tech1", "role": "staff"},
                   {"do": "signup", "who": "tech2", "role": "staff"},
                   {"do": "assign", "who": "office1", "row": "r1", "to": "tech1"},
                   {"do": "assign", "who": "tech2", "row": "r1", "to": "tech2", "must": "refused"}]},
        {"story": "A job cannot be closed without visit notes; with notes it closes and the customer rates it",
         "steps": [{"do": "signup", "who": "cust1"},
                   {"do": "create", "who": "cust1", "list": "service_requests",
                    "data": {"name": "Meena Desai", "phone": "9876500031", "address": "Baner",
                             "problem": "Noise"}, "save": "r1"},
                   {"do": "signup", "who": "tech1", "role": "staff"},
                   {"do": "set", "who": "tech1", "row": "r1", "data": {"status": "On site"}},
                   {"do": "set", "who": "tech1", "row": "r1", "data": {"status": "Done"}, "must": "refused"},
                   {"do": "set", "who": "tech1", "row": "r1",
                    "data": {"status": "Done", "visit_notes": "Fan motor badla, gas theek"}},
                   {"do": "rate", "who": "cust1", "row": "r1", "stars": 5}]},
        {"story": "A customer cannot close their own request",
         "steps": [{"do": "signup", "who": "cust1"},
                   {"do": "create", "who": "cust1", "list": "service_requests",
                    "data": {"name": "Meena Desai", "phone": "9876500031", "address": "Baner",
                             "problem": "Leak"}, "save": "r1"},
                   {"do": "set", "who": "cust1", "row": "r1", "data": {"status": "Done", "visit_notes": "khud"},
                    "must": "refused"}]},
    ],
    "not_proved": ["offline-first on a technician's phone (needs a real phone with the network cut)",
                   "photos + signature captured on a device (the fields exist; capture is the native kit's)",
                   "the 24-hour SLA firing (needs a day to pass; the rule is checked and stored)"],
}

APPS = [SCHOOL, CLINIC, FOOD, MARKET, FIELD]
ALWAYS = "None of this ran on a real phone - the plan's gate asks for that, and only a device can say it."


# ---------------------------------------------------------------- one fresh hidden app per proof
def _clear(key: str) -> int:
    """Last run's project for this proof, its twin and every row / account they held - gone before the next run."""
    from ..site import webapp as W
    n = 0
    with session() as s:
        for p in s.query(AppProject).filter(AppProject.tenant_id == TENANT).all():
            plan = json.loads(p.plan or "{}")
            mine = plan.get(TAG) == key
            twin_of = plan.get("jaanch_of")
            if not mine and twin_of:
                parent = s.get(AppProject, twin_of)
                mine = parent is not None and json.loads(parent.plan or "{}").get(TAG) == key
            if not mine:
                continue
            site = "app:" + p.id
            s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == site).delete(synchronize_session=False)
            s.query(W.SiteAppMember).filter(W.SiteAppMember.site_id == site).delete(synchronize_session=False)
            s.delete(p)
            n += 1
    return n


def _fresh(app: dict[str, Any], i: int) -> AppProject:
    from . import backend as BE
    from ..site import webapp as W
    W.ensure_tables()
    _clear(app["key"])
    with session() as s:
        r = AppProject(tenant_id=TENANT, number=f"P-{i + 1:04d}", name=app["label"], brief=app["line"],
                       field="proof", goal="catalogue", language="en", status="approved", stage="proof",
                       plan=json.dumps({TAG: app["key"]}), facts=json.dumps({"name": app["label"]}),
                       android=json.dumps({"app_key": "ak" + secrets.token_hex(12)}))
        s.add(r)
        s.flush()
        s.expunge(r)
    BE.ensure(r)
    return _get(r.id)


def _get(aid: str) -> AppProject:
    with session() as s:
        r = s.get(AppProject, aid)
        s.expunge(r)
    return r


def prove(app: dict[str, Any], i: int = 0) -> dict[str, Any]:
    """The whole road for one proof app. Every stage is reported, a failure in one stage never hides the others."""
    from . import architect as AR
    from . import backend as BE
    from . import quality as QA
    from .logic import service as LS
    t0 = time.time()
    rep: dict[str, Any] = {"key": app["key"], "label": app["label"], "line": app["line"], "modules": [],
                           "brain": {}, "scenarios": {}, "next_steps": [], "problems": [],
                           "not_proved": list(app.get("not_proved") or [])}
    r = _fresh(app, i)
    rep["app"] = r.id
    try:
        plan = AR.plan(r, app["line"], ask=lambda system, prompt: app["spec"])
    except Exception as e:                                          # noqa: BLE001
        rep["problems"].append(f"naksha: {type(e).__name__}: {str(e)[:160]}")
        return _verdict(rep, t0)
    rep["naksha_errors"] = plan["errors"]
    if plan["errors"]:
        rep["problems"] += [f"naksha: {x}" for x in plan["errors"][:5]]
    for m in plan["modules"]:
        key = m["key"]
        one: dict[str, Any] = {"key": key, "label": m["label"]}
        try:
            AR.approve(_get(r.id), key, plan["hash"])
            got = AR.build(_get(r.id), key)
            pr = got.get("proof") or {}
            one.update(state="built" if got["ok"] else "failed", done=got["done"], problems=got["problems"],
                       proof={k: pr.get(k) for k in ("ran", "pass", "fail", "total", "why")})
            rep["next_steps"] += [f"{m['label']}: {x}" for x in got["next_steps"]]
            rep["problems"] += [f"{m['label']}: {x}" for x in got["problems"]]
        except Exception as e:                                      # noqa: BLE001
            one.update(state="failed", problems=[f"{type(e).__name__}: {str(e)[:160]}"])
            rep["problems"].append(f"{m['label']}: {type(e).__name__}: {str(e)[:160]}")
        rep["modules"].append(one)

    # the brain: drafted by the build, applied HERE because this is the harness's own test app (on hers: her tap)
    r = _get(r.id)
    draft = (json.loads(r.backend or "{}").get("logic_draft") or {})
    if draft.get("hash"):
        try:
            got = LS.apply(r, draft["hash"], by="proof-harness")
            rep["brain"] = {"applied": True, "rev": got["rev"], "lines": len(got["summary"])}
        except Exception as e:                                      # noqa: BLE001
            rep["brain"] = {"applied": False, "why": f"{type(e).__name__}: {str(e)[:160]}"}
            rep["problems"].append(f"brain: {rep['brain']['why']}")
        rep["next_steps"] = [x for x in rep["next_steps"] if "Lagu karo" not in x]

    # the scenarios: written by hand, checked against the app as it now IS, played on a twin
    r = _get(r.id)
    sch = BE.schema(r)
    spec = (json.loads(r.backend or "{}").get("logic") or {}).get("spec") or {}
    ck = QA.check({"scenarios": app["scenarios"]}, sch, spec)
    if ck["errors"]:
        rep["problems"] += [f"scenario check: {x}" for x in ck["errors"][:5]]
    if ck["scenarios"]:
        run = QA.run(r, scenarios=ck["scenarios"])
        rep["scenarios"] = {"total": run.get("total", len(ck["scenarios"])), "pass": run.get("pass", 0),
                            "fail": run.get("fail", 0), "not_run": run.get("not_run", 0),
                            "failed": [{"story": s.get("story"), "why": _why(s)} for s in run.get("stories") or []
                                       if s.get("state") != "pass"]}
        rep["refused_checked"] = sum(1 for sc in ck["scenarios"] for st in sc["steps"] if st["must"] == "refused")
    return _verdict(rep, t0)


def _why(story: dict[str, Any]) -> str:
    bad = [s for s in story.get("steps") or [] if s.get("state") != "pass"]
    s = bad[0] if bad else ((story.get("steps") or [{}])[-1])
    return f"step {s.get('do')} by {s.get('who')}: {str(s.get('why') or '')[:140]}"


def _verdict(rep: dict[str, Any], t0: float) -> dict[str, Any]:
    sc = rep.get("scenarios") or {}
    mods_ok = bool(rep["modules"]) and all(m.get("state") == "built" for m in rep["modules"])
    sc_ok = bool(sc) and sc.get("fail", 1) == 0 and sc.get("not_run", 1) == 0 and sc.get("total", 0) > 0
    rep["proved"] = mods_ok and sc_ok and not rep["problems"]
    rep["seconds"] = round(time.time() - t0, 1)
    rep["says"] = (f"{rep['label']}: " + ("PROVED on the server" if rep["proved"] else "NOT proved")
                   + f" - {sum(1 for m in rep['modules'] if m.get('state') == 'built')}/{len(rep['modules'])} modules built"
                   + (f", {sc.get('pass', 0)}/{sc.get('total', 0)} scenarios pass" if sc else ", no scenario ran")
                   + (f", {rep.get('refused_checked', 0)} refusals checked" if sc else "")
                   + (f"; first problem: {rep['problems'][0][:120]}" if rep["problems"] else "")
                   + (f"; first failed: {sc['failed'][0]['story'][:60]} ({sc['failed'][0]['why'][:80]})"
                      if sc.get("failed") else ""))
    return rep


def run(only: str = "") -> dict[str, Any]:
    """The card for all five (or one). Saved, so the console / a later reading can say what was last proved."""
    from ..db import init_db
    init_db()
    picks = [a for a in APPS if not only or a["key"] == only]
    if not picks:
        raise ValueError(f"no proof app '{only}' (have: {', '.join(a['key'] for a in APPS)})")
    out = [prove(a, APPS.index(a)) for a in picks]
    card = {"at": now().isoformat(), "apps": out, "proved": sum(1 for a in out if a["proved"]), "total": len(out),
            "on_a_phone": False, "always": ALWAYS,
            "says": f"{sum(1 for a in out if a['proved'])}/{len(out)} proof apps proved on the server. {ALWAYS}"}
    _save(card)
    return card


def _save(card: dict[str, Any]) -> None:
    try:
        from ..config import settings
        from pathlib import Path
        d = Path(getattr(settings, "data_dir", "data")) / "proofapps"
        d.mkdir(parents=True, exist_ok=True)
        (d / "last.json").write_text(json.dumps(card, ensure_ascii=False, indent=1, default=str))
    except Exception:                                               # noqa: BLE001
        log.debug("proofapps save", exc_info=True)


def main(argv: list[str]) -> int:
    only = argv[argv.index("--only") + 1] if "--only" in argv and argv.index("--only") + 1 < len(argv) else ""
    card = run(only)
    for a in card["apps"]:
        print(a["says"])
        for s in a["next_steps"][:6]:
            print("   needs her:", s[:150])
        for x in a["not_proved"]:
            print("   not proved:", x[:150])
    print(card["says"])
    if "--json" in argv:
        print(json.dumps(card, ensure_ascii=False, indent=1, default=str))
    return 0 if card["proved"] == card["total"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
