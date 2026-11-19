"""Starter recipes: a brief with blanks. These are Hoola's STARTERS - the page says so; nothing here claims a kept
rate (that needs the outcome ledger, plan P4). Web starters are the Web Studio's own 1,00,000 website templates."""
from __future__ import annotations

import re
from typing import Any

from . import anatomy as A
from . import brief as B

B_NAME = {"key": "business", "label": "Business name", "eg": "Shree Balaji Sweets"}
B_CITY = {"key": "city", "label": "City", "eg": "Akola"}
B_OFFER = {"key": "offer", "label": "The offer, exactly", "eg": "Flat 30% Off"}
B_PRODUCT = {"key": "product", "label": "Product or service", "eg": "kaju katli"}
B_PRICE = {"key": "price", "label": "Price, exactly", "eg": "Rs 499"}
B_FEST = {"key": "festival", "label": "Festival", "eg": "Diwali"}
B_AUD = {"key": "audience", "label": "Who it is for", "eg": "families in Akola"}

_IMAGE = [
    ("img-festival-offer", "Festival offer poster", "a festive poster with your offer in large words",
     "{festival} offer poster for {business}", [B_FEST, B_NAME, B_OFFER],
     {"subject": "one clear {festival} symbol with a few flowers beside it", "scene": "on a dark, uncluttered surface",
      "style": "Festive poster", "words": "{festival} Sale - {offer}", "size": "4:5",
      "composition": "the symbol in the lower third, clear empty space in the upper half for the words",
      "light": "warm glow, dark background"}),
    ("img-product-photo", "Product photo", "a clean close-up photo of one product",
     "product photo of {product} for {business}", [B_PRODUCT, B_NAME],
     {"subject": "{product}, shown at its best", "scene": "on a clean counter or table", "style": "Product photo", "size": "1:1",
      "composition": "close-up from a 45 degree angle, the product fills most of the frame, soft blurred background",
      "light": "soft daylight from a window on one side"}),
    ("img-festival-wish", "Festival greeting", "a greeting picture with your shop's wishes",
     "{festival} greeting from {business}", [B_FEST, B_NAME],
     {"subject": "a simple, respectful {festival} scene", "style": "Flat illustration", "words": "Happy {festival} - {business}",
      "size": "1:1", "composition": "the scene in the centre, room at the top for the words", "light": "even bright light"}),
    ("img-price-offer", "Price offer post", "a square post with one product and its price",
     "offer post: {product} at {price}", [B_PRODUCT, B_PRICE, B_NAME],
     {"subject": "{product}", "scene": "on a plain coloured background", "style": "Product photo",
      "words": "{product} - {price}", "size": "1:1", "composition": "the product on the left two thirds, the words on the right"}),
    ("img-admission", "Admissions open poster", "a poster for school, coaching or class admissions",
     "admissions open poster for {business}", [B_NAME, {"key": "year", "label": "Session", "eg": "2027-28"}],
     {"subject": "three smiling students with bags", "scene": "in front of the institute's gate", "style": "Real photograph",
      "words": "Admissions Open {year}", "size": "4:5",
      "composition": "students on the left half, a plain coloured panel on the right for the words", "light": "morning sunlight"}),
    ("img-hiring", "We are hiring post", "a simple hiring post",
     "hiring post for {business}", [B_NAME, {"key": "role", "label": "Role", "eg": "Sales Executive"}],
     {"subject": "a tidy desk with a laptop, a mug and a small plant", "style": "Flat illustration",
      "words": "We Are Hiring - {role}", "size": "1:1", "composition": "desk in the lower half, plain wall above for the words"}),
    ("img-banner", "Website / shop banner", "a wide banner for a website header or shop board",
     "wide banner for {business}", [B_NAME, B_PRODUCT],
     {"subject": "{product}", "scene": "inside the shop, softly blurred behind", "style": "Real photograph", "size": "16:9",
      "words": "{business}", "composition": "the product on the right third, soft empty space on the left for the words"}),
    ("img-logo", "Simple logo idea", "a simple two-colour logo to start from",
     "logo for {business}", [B_NAME, {"key": "symbol", "label": "One symbol", "eg": "a clay cup of chai"}],
     {"subject": "{symbol}", "scene": "on a plain background", "style": "Simple logo", "words": "{business}", "size": "1:1",
      "composition": "the symbol in the centre, nothing else around it", "colours": "two colours only"}),
    ("img-thumbnail", "Video thumbnail", "a punchy wide thumbnail with big words",
     "thumbnail for my video about {product}", [B_PRODUCT, {"key": "title", "label": "3-4 words on it", "eg": "10 Minute Paneer"}],
     {"subject": "{product}, in a tight close-up", "style": "Real photograph", "words": "{title}", "size": "16:9",
      "composition": "the subject fills the left two thirds, big bold words on the right", "light": "strong warm light"}),
    ("img-story", "Story announcement", "a vertical story for WhatsApp or Instagram",
     "story announcing {offer} at {business}", [B_OFFER, B_NAME],
     {"subject": "the shop front or the main product", "style": "Festive poster", "words": "{offer}", "size": "9:16",
      "composition": "the subject in the middle third, words in the top third, the bottom third left clear"}),
]
_SCRIPT = [
    ("scr-festival-reel", "Festival offer reel", "a 30-second reel for a festival offer",
     "{festival} reel script for {business}", [B_FEST, B_NAME, B_OFFER, B_AUD],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "{audience}",
      "message": "{business} is where the family's {festival} shopping starts", "hook": "a small, real family moment just before {festival}",
      "cta": "Message on WhatsApp", "tone": "Warm"}, "Offer: {offer}"),
    ("scr-shop-intro", "Shop introduction", "a short video that introduces your shop",
     "introduction video script for {business} in {city}", [B_NAME, B_CITY, B_PRODUCT],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "people in {city} who have not visited yet",
      "message": "what makes {business} worth one visit for {product}", "hook": "the shutter going up in the morning",
      "cta": "Visit the shop", "tone": "Warm"}, ""),
    ("scr-product-launch", "New product launch", "a reel announcing something new",
     "launch reel for {product} at {business}", [B_PRODUCT, B_NAME, B_PRICE],
     {"platform": "Instagram reel", "length": "20 seconds", "audience": "our regular customers",
      "message": "{product} is here and it is worth trying this week", "hook": "hands unboxing {product} for the first time",
      "cta": "Message on WhatsApp", "tone": "Energetic"}, "Price: {price}"),
    ("scr-customer-story", "Customer story", "a short, honest customer moment",
     "customer story video for {business}", [B_NAME, B_AUD],
     {"platform": "Instagram reel", "length": "45 seconds", "audience": "{audience}",
      "message": "the small problem {business} quietly solves", "hook": "the customer's problem, shown without words",
      "cta": "Message on WhatsApp", "tone": "Emotional"}, ""),
    ("scr-whatsapp-status", "WhatsApp status video", "a 15-second status for today's offer",
     "whatsapp status video for today's offer at {business}", [B_NAME, B_OFFER],
     {"platform": "WhatsApp status video", "length": "15 seconds", "audience": "people who already have our number",
      "message": "today's offer, said once and clearly", "cta": "Message on WhatsApp", "tone": "Funny"}, "Offer: {offer}"),
    ("scr-explainer", "How it works explainer", "a one-minute explainer of your service",
     "explainer video script: how {product} from {business} works", [B_PRODUCT, B_NAME, B_AUD],
     {"platform": "YouTube video", "length": "60 seconds", "audience": "{audience}",
      "message": "{product} in three plain steps", "hook": "the everyday trouble before {product}",
      "cta": "Call now", "tone": "Straight and honest"}, ""),
    ("scr-hiring", "Hiring video", "a short video to attract the right applicants",
     "hiring video script for {business}", [B_NAME, {"key": "role", "label": "Role", "eg": "delivery partners"}],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "people looking for work as {role}",
      "message": "what a normal day and a fair deal look like at {business}", "cta": "Call now", "tone": "Straight and honest"}, ""),
    ("scr-testimonial-ask", "Admission / season opening", "a video for admissions or a new season",
     "admissions video script for {business}", [B_NAME, B_AUD, {"key": "date", "label": "Last date / start date", "eg": "15 June"}],
     {"platform": "Instagram reel", "length": "30 seconds", "audience": "{audience}",
      "message": "why this is the year to join {business}", "hook": "a question a child or a customer really asks",
      "cta": "Call now", "tone": "Warm"}, "Date: {date}"),
]
B_DATE = {"key": "date", "label": "Last date, exactly", "eg": "15 Nov"}
_APP = [
    ("app-kirana-order", "Order and delivery app", "an app where customers order and you deliver",
     "an order and home delivery app for {business} in {city}", [B_NAME, B_CITY],
     {"what": "{business} in {city}: customers order and we deliver at home", "users": "Customers and staff",
      "job": "Place an order", "lists": "products with price, photo and stock; orders with status; customers",
      "money": "UPI to my account", "alerts": "order accepted, out for delivery, delivered", "platform": "Android"}),
    ("app-clinic-booking", "Appointment booking app", "an app for patients to book a time",
     "an appointment booking app for {business}", [B_NAME, {"key": "doctor", "label": "Doctor / staff names", "eg": "Dr. Patil"}],
     {"what": "{business}: patients book a time with {doctor}", "users": "Patients", "job": "Book a slot",
      "lists": "time slots per day, bookings, patients", "money": "No payments in the app",
      "alerts": "booking confirmed, reminder one hour before", "platform": "Android and iPhone"}),
    ("app-school-fees", "School / coaching app", "an app for parents to see attendance and pay fees",
     "a parents app for {business}", [B_NAME],
     {"what": "{business}: parents see attendance, homework and fees", "users": "Students and parents",
      "job": "See and pay a bill", "lists": "students, classes, attendance, fees due", "money": "UPI to my account",
      "alerts": "absent today, fee due, new homework", "language": "English and Hindi"}),
    ("app-staff-field", "Staff field app", "an app for your staff to take and finish jobs",
     "a field staff app for {business}", [B_NAME, {"key": "work", "label": "The work", "eg": "AC service visits"}],
     {"what": "{business}: staff get {work} jobs and mark them done with a photo", "users": "My staff",
      "job": "Mark attendance", "lists": "jobs with address, status and photo; staff", "money": "No payments in the app",
      "alerts": "new job given to you", "platform": "Android"}),
]
_VIDEO = [
    ("vid-product-hero", "Product hero clip", "a slow close-up of one product for a reel",
     "a short close-up clip of {product}", [B_PRODUCT],
     {"subject": "{product}", "action": "it turns slowly so every side catches the light", "camera": "Slow push in",
      "place": "on a clean dark surface", "light": "Warm evening glow", "style": "Product advert", "size": "9:16",
      "length": "8 seconds"}),
    ("vid-shop-open", "Shop opening clip", "the shutter going up in the morning",
     "a morning clip of {business} opening", [B_NAME],
     {"subject": "the front of {business}", "action": "the shutter rolls up and the lights inside come on",
      "camera": "Still camera", "light": "Soft morning light", "style": "Real film", "size": "9:16", "length": "8 seconds"}),
    ("vid-food-pour", "Food or drink close-up", "a mouth-watering pour or sizzle",
     "a close-up clip of {product} being served", [B_PRODUCT],
     {"subject": "{product} in a simple bowl or cup", "action": "it is poured or served and steam rises",
      "camera": "Slow push in", "light": "Warm evening glow", "style": "Slow-motion close-up", "size": "9:16",
      "length": "5 seconds"}),
    ("vid-festival-diya", "Festival mood clip", "a calm festive scene for a greeting",
     "a {festival} mood clip for {business}", [B_FEST, B_NAME],
     {"subject": "a row of small lamps on a doorstep", "action": "a hand lights the last lamp", "camera": "Slow pan left to right",
      "light": "Festive lamps at night", "style": "Real film", "size": "9:16", "length": "8 seconds"}),
]
_MUSIC = [
    ("mus-shop-jingle", "Shop jingle", "a short catchy jingle with your shop's name",
     "a jingle for {business}", [B_NAME],
     {"use": "Shop jingle", "genre": "Bollywood pop", "mood": "Happy", "vocals": "Female voice", "language": "Hinglish",
      "tempo": "Medium", "lyrics": "{business}", "length": "15 seconds"}),
    ("mus-reel-bgm", "Reel background music", "music under a reel, no singing",
     "background music for my reels", [],
     {"use": "Reel background", "genre": "Lo-fi", "mood": "Calm", "vocals": "Instrumental, no singing", "tempo": "Medium",
      "length": "30 seconds"}),
    ("mus-festival-song", "Festival song", "a short festive song for greetings",
     "a {festival} song for {business}", [B_FEST, B_NAME],
     {"use": "Festival song", "genre": "Folk", "mood": "Festive", "vocals": "Duet", "language": "Hindi",
      "instruments": "dholak, flute and bells", "tempo": "Fast", "length": "60 seconds"}),
    ("mus-devotional", "Devotional music", "a calm devotional piece",
     "calm devotional music for {festival}", [B_FEST],
     {"use": "Event / wedding", "genre": "Devotional", "mood": "Calm", "vocals": "Instrumental, no singing",
      "instruments": "flute, tanpura and soft bells", "tempo": "Slow", "length": "2 minutes"}),
]
_MARKETING = [
    ("mkt-wa-offer", "WhatsApp offer message", "a short offer message for your regular customers",
     "a WhatsApp offer message from {business}", [B_NAME, B_OFFER, B_DATE],
     {"channel": "WhatsApp message", "audience": "My regular customers", "offer": "{offer} till {date}",
      "action": "Reply on WhatsApp", "tone": "Warm and friendly", "sender": "{business}"}, "Offer: {offer} till {date}"),
    ("mkt-winback", "Come back message", "a gentle message to customers who stopped coming",
     "a come-back message from {business}", [B_NAME, B_OFFER],
     {"channel": "WhatsApp message", "audience": "Customers who have not come back", "offer": "{offer} on your next visit",
      "action": "Visit the shop", "tone": "Warm and friendly", "sender": "{business}"}, "Offer: {offer}"),
    ("mkt-email-news", "Email newsletter", "a monthly email with your news",
     "this month's newsletter email from {business}", [B_NAME, {"key": "news", "label": "The news", "eg": "new branch in Ramdaspeth"}],
     {"channel": "Email", "audience": "My regular customers", "offer": "{news}", "action": "Visit the shop",
      "tone": "Warm and friendly", "sender": "{business}"}),
    ("mkt-insta-caption", "Instagram caption", "a caption for a post about one product",
     "an Instagram caption for {product} at {business}", [B_PRODUCT, B_NAME],
     {"channel": "Instagram caption", "audience": "New customers", "offer": "{product} is now available",
      "action": "Order online", "tone": "Short and direct"}),
    ("mkt-admission-sms", "Admissions SMS", "a short SMS for admissions",
     "an admissions SMS for {business}", [B_NAME, B_DATE],
     {"channel": "SMS", "audience": "Students and parents", "offer": "Admissions open, last date {date}",
      "action": "Call now", "tone": "Respectful and formal", "sender": "{business}"}, "Last date: {date}"),
]
_DOC = [
    ("doc-quotation", "Quotation", "a quotation with a price table",
     "a quotation from {business} for {client}", [B_NAME, {"key": "client", "label": "Client name", "eg": "ABC Industries"},
                                                    {"key": "items", "label": "Items with prices", "eg": "AMC for 10 ACs Rs 45,000"}],
     {"kind": "Quotation", "reader": "the purchase team at {client}", "purpose": "approve and place the order",
      "content": "{items}", "parts": "items with price table, GST, validity, payment terms", "tone": "Formal",
      "length": "One page", "format": "PDF", "sender": "{business}"}, "Items: {items}"),
    ("doc-proposal", "Business proposal", "a proposal for a new client",
     "a proposal from {business} to {client}", [B_NAME, {"key": "client", "label": "Client name", "eg": "Green Valley School"},
                                                  {"key": "service", "label": "What you offer", "eg": "a school website and app"}],
     {"kind": "Proposal", "reader": "the decision maker at {client}", "purpose": "agree to {service}",
      "parts": "their need, what we will do, timeline, price, why us, next step", "tone": "Friendly and professional",
      "length": "Two to three pages", "format": "PDF", "sender": "{business}"}),
    ("doc-notice", "Notice to customers or staff", "a short notice, like a holiday or a price change",
     "a notice from {business}: {news}", [B_NAME, {"key": "news", "label": "What the notice says", "eg": "shop closed on 12 Nov"}],
     {"kind": "Notice", "reader": "our customers", "purpose": "know {news}", "content": "{news}", "tone": "Simple and plain",
      "length": "One page", "format": "PDF", "sender": "{business}"}),
    ("doc-monthly-report", "Monthly report", "a one-page report of a month's work",
     "a monthly report for {business} for {month}", [B_NAME, {"key": "month", "label": "Month", "eg": "October 2026"}],
     {"kind": "Report", "reader": "the owner and partners", "purpose": "see how {month} went and what to fix",
      "parts": "summary, numbers, what went well, problems, next month's plan", "tone": "Simple and plain",
      "length": "One page", "format": "PDF", "sender": "{business}"}),
    ("doc-offer-letter", "Job offer letter", "an offer letter for a new staff member",
     "an offer letter from {business} to {person}", [B_NAME, {"key": "person", "label": "Person's name", "eg": "Rahul Jadhav"},
                                                      {"key": "role", "label": "Role", "eg": "Sales Executive"}],
     {"kind": "Letter", "reader": "{person}", "purpose": "accept the {role} job", "parts": "role, start date, salary, "
      "working hours, leave, how to accept", "tone": "Friendly and professional", "length": "One page",
      "format": "Word document", "sender": "{business}"}),
]
_CODE = [
    ("code-fix-bug", "Fix a bug", "a bug fix proved by a test that fails first",
     "fix: {problem}", [{"key": "problem", "label": "What goes wrong", "eg": "the cart total shows Rs 0 after a coupon"},
                         {"key": "expected", "label": "What should happen", "eg": "Rs 500 with 10% off shows Rs 450"}],
     {"kind": "Fix a bug", "task": "{problem}", "done": "{expected}", "check": "Add a test that fails first",
      "rules": "change as little as possible; keep every other test passing"}),
    ("code-feature", "Add a small feature", "a new feature with its own tests",
     "add a feature: {feature}", [{"key": "feature", "label": "The feature", "eg": "a 'Reorder' button on past orders"},
                                  {"key": "expected", "label": "Done means", "eg": "one tap puts the same items in the cart"}],
     {"kind": "New feature", "task": "{feature}", "done": "{expected}", "check": "Run the tests",
      "rules": "follow the project's existing style; no new libraries unless asked"}),
    ("code-tests", "Add tests", "tests for code that has none",
     "add tests for {area}", [{"key": "area", "label": "Which code", "eg": "the GST invoice maker"}],
     {"kind": "Add tests", "task": "write tests for {area}, the normal case and the edge cases",
      "done": "the new tests pass and would fail if the code were broken", "check": "Run the tests",
      "avoid": "the code being tested - only add tests"}),
    ("code-explain", "Explain some code", "a plain explanation of how a part works",
     "explain how {area} works", [{"key": "area", "label": "Which code", "eg": "the login flow"}],
     {"kind": "Explain the code", "task": "explain how {area} works, file by file, in plain words",
      "done": "I can follow the path of one request from start to end", "check": "I will check by hand",
      "avoid": "everything - read only, change nothing"}),
]
_RESEARCH = [
    ("res-compare-options", "Compare options", "a side-by-side table to choose between options",
     "compare {options} for {business}", [{"key": "options", "label": "The options", "eg": "Shiprocket, Delhivery and India Post"}, B_NAME],
     {"question": "how {options} compare on price, speed and service", "decision": "which one {business} should use",
      "parts": "price, time, coverage, hidden charges, what users complain about", "sources": "Company websites",
      "asof": "The latest", "form": "A comparison table"}),
    ("res-rules", "Rules and licences", "what the law needs for your business",
     "which licences and rules apply to {kind_of} in {city}", [{"key": "kind_of", "label": "Kind of business", "eg": "a home bakery"}, B_CITY],
     {"question": "which licences, registrations and rules apply to {kind_of} in {city}",
      "decision": "what to apply for first", "parts": "licence name, who issues it, fee, documents, time it takes",
      "sources": "Official / government sites first", "region": "{city}", "asof": "The latest", "form": "A report with sources"}),
    ("res-market", "Market check", "how big a market is and who is in it",
     "market for {product} in {city}", [B_PRODUCT, B_CITY],
     {"question": "how big the market for {product} is in {city} and who the main sellers are",
      "decision": "whether to start selling {product} here", "parts": "demand signs, main competitors, their prices, gaps",
      "sources": "Any reliable source", "region": "{city}", "asof": "Last 12 months", "form": "A report with sources"}),
    ("res-schemes", "Government schemes", "schemes and loans your business may get",
     "government schemes for {kind_of}", [{"key": "kind_of", "label": "Kind of business", "eg": "a women-run food business"}],
     {"question": "which central and state schemes, loans or subsidies {kind_of} can apply for",
      "decision": "which scheme to apply for", "parts": "scheme name, benefit, who qualifies, how to apply, last date",
      "sources": "Official / government sites first", "region": "India", "asof": "This year", "form": "A comparison table"}),
]
_DATA = [
    ("data-top-products", "Top products", "which products earn the most",
     "top products in {file}", [{"key": "file", "label": "File or sheet", "eg": "sales_october.xlsx"}],
     {"data": "{file}", "question": "which 10 products made the most money and the most profit",
      "output": "A table", "checks": "the totals must match the sheet's own total"}),
    ("data-monthly-chart", "Sales by month chart", "a chart of sales month by month",
     "sales by month chart from {file}", [{"key": "file", "label": "File or sheet", "eg": "sales_2026.xlsx"}],
     {"data": "{file}", "question": "total sales by month, and which month grew or fell most", "output": "A chart"}),
    ("data-dues", "Who owes money", "the list of pending payments, oldest first",
     "pending payments from {file}", [{"key": "file", "label": "File or sheet", "eg": "udhaar.xlsx"}],
     {"data": "{file}", "question": "who owes money, how much, and since when, oldest first", "output": "A table",
      "checks": "the total due must equal the sum of every pending row"}),
    ("data-formula", "A sheet formula", "a formula to paste into Excel or Google Sheets",
     "a formula for {need}", [{"key": "need", "label": "What the formula should do", "eg": "the GST amount in column D"}],
     {"data": "my sheet", "question": "a formula for {need}", "output": "A formula for my sheet"}),
]
_AIAPP = [
    ("ai-faq", "Answers questions", "an AI that answers customers' common questions",
     "an AI that answers customers of {business}", [B_NAME, {"key": "facts", "label": "Timings, prices, policies", "eg": "open 10 am to 8 pm, closed Tuesday"}],
     {"role": "Answer questions", "business": "{business}", "knows": "{facts}",
      "never": "never promise a discount or a time not in the facts; never share anyone's details", "handoff": "A question it cannot answer",
      "tone": "Warm and friendly", "language": "The customer's own language", "channel": "My WhatsApp number"}, "Facts: {facts}"),
    ("ai-booking", "Takes bookings", "an AI that books appointments",
     "a booking assistant for {business}", [B_NAME, {"key": "facts", "label": "Services, prices and timings", "eg": "haircut Rs 300, 10 am to 8 pm"}],
     {"role": "Take bookings", "business": "{business}", "knows": "{facts}",
      "never": "never book outside the timings; never confirm a price that is not in the facts", "handoff": "A booking change",
      "tone": "Short and polite", "language": "The customer's own language", "channel": "My WhatsApp number"}, "Facts: {facts}"),
    ("ai-enquiry", "Collects enquiries", "an AI that takes a lead's details for you",
     "an enquiry assistant for {business}", [B_NAME, {"key": "facts", "label": "What you offer", "eg": "solar panels for homes, 3 to 10 kW"}],
     {"role": "Collect enquiries", "business": "{business}", "knows": "{facts}",
      "never": "never quote a price or a delivery date; never ask for a card number or OTP", "handoff": "Anyone who asks for a person",
      "tone": "Warm and friendly", "channel": "My website"}, "Offer: {facts}"),
    ("ai-support", "After-sale support", "an AI that helps after a purchase",
     "a support assistant for {business}", [B_NAME, {"key": "facts", "label": "Warranty and return rules", "eg": "7 day return, 1 year warranty"}],
     {"role": "Support after a sale", "business": "{business}", "knows": "{facts}",
      "never": "never promise a refund; never blame the customer", "handoff": "A complaint",
      "tone": "Short and polite", "language": "The customer's own language"}, "Rules: {facts}"),
]
_CHAT = [
    ("chat-reply-customer", "Reply to a customer", "a calm reply to a customer's message",
     "a reply to a customer who says {issue}", [{"key": "issue", "label": "What the customer said", "eg": "the cake came 40 minutes late"}],
     {"goal": "a reply to a customer who says {issue}", "context": "keep the customer; say sorry once, no excuses",
      "form": "A message I can send", "avoid": "promising a refund or discount I did not offer"}),
    ("chat-names", "Name ideas", "names for a shop, product or offer",
     "name ideas for {thing}", [{"key": "thing", "label": "Name for what", "eg": "a new tea stall near the station"}],
     {"goal": "10 name ideas for {thing}", "form": "A list of ideas", "avoid": "names already used by big brands"}),
    ("chat-plan-week", "Plan my week", "a simple plan for the week's work",
     "a plan for this week: {work}", [{"key": "work", "label": "The work", "eg": "Diwali orders, 2 staff on leave, a bank visit"}],
     {"goal": "a day-by-day plan for this week: {work}", "form": "Steps"}),
    ("chat-explain", "Explain simply", "a plain explanation of something new",
     "explain {topic} simply", [{"key": "topic", "label": "What to explain", "eg": "how GST input credit works"}],
     {"goal": "explain {topic} in plain words with one everyday example", "form": "A short answer"}),
]
_BLANK = re.compile(r"\{([a-z_]+)\}")


def _mk(t, section: str) -> dict[str, Any]:
    rid, title, makes, intent, blanks, slots = t[:6]
    return {"id": rid, "section": section, "title": title, "makes": makes, "intent": intent, "blanks": blanks,
            "slots": slots, "facts": t[6] if len(t) > 6 else "", "starter": True}


RECIPES: list[dict[str, Any]] = [*[_mk(t, "image") for t in _IMAGE], *[_mk(t, "script") for t in _SCRIPT],
                                  *[_mk(t, "app") for t in _APP], *[_mk(t, "video") for t in _VIDEO],
                                  *[_mk(t, "music") for t in _MUSIC], *[_mk(t, "marketing") for t in _MARKETING],
                                  *[_mk(t, "doc") for t in _DOC], *[_mk(t, "code") for t in _CODE],
                                  *[_mk(t, "research") for t in _RESEARCH], *[_mk(t, "data") for t in _DATA],
                                  *[_mk(t, "aiapp") for t in _AIAPP], *[_mk(t, "chat") for t in _CHAT]]


def listing(section: str = "", q: str = "", limit: int = 30) -> dict[str, Any]:
    """Recipes for the shelf. `web` comes from the Web Studio's template library (search by trade, city, style)."""
    out: list[dict[str, Any]] = []
    words = [w for w in (q or "").lower().split() if w]
    if section != "web":
        for r in RECIPES:
            if section and r["section"] != section:
                continue
            hay = (r["title"] + " " + r["makes"] + " " + r["intent"]).lower()
            if all(w in hay for w in words):
                out.append({k: r[k] for k in ("id", "section", "title", "makes", "blanks", "starter")})
    if section != "web":                         # P11 SAMUDAAY: approved community recipes (none while switched off)
        try:
            from . import samudaay as SM
            out.extend(SM.listing(section, q))
        except Exception:       # noqa: BLE001
            pass
    try:                                         # NATIJA KHATA: recipes whose results were kept come first, with the count
        from . import ledger as L
        rates = L.recipe_rates()
        for r in out:
            if r["id"] in rates:
                r["kept"] = rates[r["id"]]
        out.sort(key=lambda r: -(r["kept"]["kept"] / r["kept"]["of"]) if r.get("kept") else 1)
    except Exception:       # noqa: BLE001
        pass
    total = len(out)
    if section in ("", "web"):
        try:
            from ..site import templates as T
            got = T.search(q=q or "", limit=min(limit, 24))
            for c in got.get("items") or got.get("rows") or []:
                out.append({"id": f"web:{c.get('id')}", "section": "web", "title": c.get("title") or c.get("name") or "Website",
                            "makes": str(c.get("line") or "") + (f" - {c['style_label']}" if c.get("style_label") else ""),
                            "blanks": [], "starter": True})
            total += int(got.get("total") or 0)
        except Exception:       # noqa: BLE001 - the template library is optional here
            pass
    return {"items": out[:limit + 24], "total": total}


def _sub(text: str, values: dict[str, str]) -> tuple[str, bool]:
    """`text` with its blanks filled; the bool is False when a blank is still empty."""
    full = True

    def rep(m):
        nonlocal full
        v = str(values.get(m.group(1)) or "").strip()
        if not v:
            full = False
            return "[" + m.group(1).replace("_", " ") + "]"
        return v[:120]
    return _BLANK.sub(rep, text), full


def use(recipe_id: str, values: dict[str, str] | None = None) -> dict[str, Any]:
    """A recipe with her values -> {"brief": ...} (every section but web) or {"ready": finished prompt} (a web template).
    A slot whose blank she left empty is LEFT OUT (it becomes a question), never filled with a made-up value."""
    values = {str(k): str(v) for k, v in (values or {}).items()}
    if recipe_id.startswith("web:"):
        from ..site import templates as T
        p = T.prompt(recipe_id[4:])
        return {"ready": {"section": "web", "title": p.get("title") or "Website", "prompt": p["prompt"],
                          "run": {"to": "web", "text": p["prompt"], "label": "Open in Web Studio"}}}
    if recipe_id.startswith("com:"):             # P11 SAMUDAAY: an approved community recipe, screened again
        from . import samudaay as SM
        return SM.use(recipe_id)
    r = next((x for x in RECIPES if x["id"] == recipe_id), None)
    if r is None:
        raise ValueError("No such recipe.")
    intent, _ = _sub(r["intent"], values)
    facts, full = _sub(r.get("facts") or "", values)
    if facts and full:
        intent += ". " + facts
    slots: dict[str, Any] = {}
    try:                                         # P10: a recipe value the owner changed after it was shown to keep better
        from . import khud as K
        changed = K.recipe_values(r["id"])
    except Exception:       # noqa: BLE001
        changed = {}
    for k, v in {**r["slots"], **changed}.items():
        text, ok = _sub(v, values)
        if ok:
            slots[k] = {"value": text, "source": "recipe"}
    raw = {"section": r["section"], "intent": intent, "slots": slots, "recipe_id": r["id"]}
    return {"brief": B.validate(raw)}


def check() -> list[str]:
    """Every starter is well-formed (run by a test): known slots only, blanks declared, no magic phrase."""
    bad: list[str] = []
    for r in RECIPES:
        declared = {b["key"] for b in r["blanks"]}
        used = set(_BLANK.findall(r["intent"] + " " + " ".join(r["slots"].values()) + " " + (r.get("facts") or "")))
        if used - declared:
            bad.append(f"{r['id']}: undeclared blanks {sorted(used - declared)}")
        if set(r["slots"]) - set(A.keys(r["section"])):
            bad.append(f"{r['id']}: unknown slots")
        if any(m in (r["intent"] + " ".join(r["slots"].values())).lower() for m in B.MAGIC):
            bad.append(f"{r['id']}: magic phrase")
    if len({r["id"] for r in RECIPES}) != len(RECIPES):
        bad.append("duplicate ids")
    return bad
