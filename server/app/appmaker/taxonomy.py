"""v0.128 The app design library's fixed parts: 10 app goals, 10 premium app design styles, 51 screen types with 6 designs
each (306 screen designs), 6 screens written by code (splash, consent, privacy, delete account, seller details,
notification pre-ask), 40 motion presets, navigation patterns, the industry defaults and the app-store / India rules.

The 1,000 business types (field cards) are the same ones the website library uses (`app.site.libdata`), so
1,000 fields x 10 app goals x 10 styles = 1,00,000 ready app briefs. Palettes (50) and font pairs (30) are shared with the
website library too, so a business's site and app can look like one brand.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------- app goals (10)
# screens: in the order a customer meets them; tabs: bottom navigation (max 5); flow: the main path shown on the plan.
GOALS: dict[str, dict[str, Any]] = {
    "shop": {"label": "Order & delivery", "hi": "order aur delivery", "accounts": True, "money": True,
             "screens": ["onboarding", "login", "home", "search", "categories", "product_list", "product_detail", "cart",
                         "checkout", "payment", "order_success", "orders", "order_track", "offers", "store_info", "notifications",
                         "profile", "support"],
             "tabs": ["home", "categories", "cart", "orders", "profile"],
             "flow": ["home", "product_list", "product_detail", "cart", "checkout", "payment", "order_success", "order_track"],
             "words": ["order", "orders", "delivery", "home delivery", "cart", "kharid", "kharidna", "buy", "saman mangwa", "online order",
                       "grocery", "shopping", "mangao", "ghar pe"],
             "brief": "Customers find an item in 2 taps, add to cart, pick delivery or pickup and pay by UPI to her own UPI ID. "
                      "Her real stock list drives the catalogue; out-of-stock items are shown greyed, never hidden prices."},
    "food_order": {"label": "Menu & food orders", "hi": "menu aur khana order", "accounts": True, "money": True,
                   "screens": ["onboarding", "login", "home", "menu", "dish_detail", "cart", "checkout", "payment", "order_success",
                               "order_track", "orders", "offers", "store_info", "profile", "support"],
                   "tabs": ["home", "menu", "orders", "profile"],
                   "flow": ["home", "menu", "dish_detail", "cart", "checkout", "payment", "order_success", "order_track"],
                   "words": ["menu", "khana", "food", "thali", "tiffin", "parcel", "dish", "restaurant app", "food order", "pizza",
                             "biryani", "cafe"],
                   "brief": "A menu that is a joy to scroll: categories, veg / non-veg marks, her prices, today's special; add with "
                            "options (size, spice, extra), order for delivery or pickup, live order status."},
    "booking": {"label": "Bookings & appointments", "hi": "booking aur appointment", "accounts": True, "money": True,
                "screens": ["onboarding", "login", "home", "services", "service_detail", "staff", "slot_picker", "booking_confirm",
                            "my_bookings", "store_info", "notifications", "profile", "support"],
                "tabs": ["home", "services", "my_bookings", "profile"],
                "flow": ["home", "services", "service_detail", "staff", "slot_picker", "booking_confirm", "my_bookings"],
                "words": ["booking", "book", "appointment", "slot", "token", "opd", "reserve", "time lena", "apointment"],
                "brief": "Fill her calendar: pick a service, a person (doctor / stylist / trainer) if she has a team, a free slot from "
                         "Hoola's appointment book, confirm; reminders, reschedule and cancel in one tap."},
    "learning": {"label": "Classes & learning", "hi": "padhai aur classes", "accounts": True, "money": True,
                 "screens": ["onboarding", "login", "home", "courses", "course_detail", "lesson", "quiz", "timetable", "fees",
                             "payment", "notifications", "profile", "support"],
                 "tabs": ["home", "courses", "timetable", "profile"],
                 "flow": ["home", "courses", "course_detail", "lesson", "quiz", "timetable", "fees"],
                 "words": ["course", "courses", "class", "classes", "tuition", "coaching", "padhai", "students", "notes", "test",
                           "quiz", "batch", "lecture", "homework"],
                 "brief": "Students see today's classes, notes and tests; parents see attendance and fees due. Fees for classes "
                          "at her centre are a service (UPI to her); recorded courses sold inside the app would be digital goods "
                          "(store billing) - keep them free inside the app or sell them outside it."},
    "membership": {"label": "Membership & passes", "hi": "membership aur pass", "accounts": True, "money": True,
                   "screens": ["onboarding", "login", "home", "plans", "member_card", "checkin", "timetable", "progress", "fees",
                               "payment", "notifications", "profile"],
                   "tabs": ["home", "timetable", "member_card", "profile"],
                   "flow": ["home", "plans", "fees", "payment", "member_card", "checkin", "progress"],
                   "words": ["membership", "member", "plan", "plans", "pass", "renew", "gym", "club", "check in", "checkin",
                             "monthly fee"],
                   "brief": "Members carry their pass (QR) in the app, see class timings, check in, track progress and renew "
                            "before the plan ends. Prices only as she gives them."},
    "service_request": {"label": "Service requests & repairs", "hi": "complaint aur repair", "accounts": True, "money": True,
                        "screens": ["onboarding", "login", "home", "services", "request_service", "job_status", "estimate",
                                    "invoice", "payment", "store_info", "notifications", "profile", "support"],
                        "tabs": ["home", "request_service", "job_status", "profile"],
                        "flow": ["home", "request_service", "job_status", "estimate", "invoice", "payment"],
                        "words": ["complaint", "repair", "service request", "technician", "mechanic", "job", "ticket", "fault",
                                  "kharab", "theek", "install", "installation", "breakdown", "internet band"],
                        "brief": "Customers raise a request with a photo in under a minute, see who is coming and when, approve "
                                 "extra work line by line, get the bill and pay by UPI; warranty lives in the app."},
    "khata": {"label": "Khata, bills & loyalty", "hi": "khata, bill aur points", "accounts": True, "money": True,
              "screens": ["login", "home", "khata", "invoice", "payment", "rewards", "offers", "notifications", "store_info",
                          "profile", "support"],
              "tabs": ["home", "khata", "rewards", "profile"],
              "flow": ["home", "khata", "invoice", "payment", "rewards"],
              "words": ["khata", "udhaar", "udhar", "baaki", "dues", "ledger", "bill", "bills", "loyalty", "points", "regular customer",
                        "hisaab", "credit"],
              "brief": "Regular customers see what they owe (and what they paid) line by line, get gentle reminders, pay by UPI "
                       "and earn points she decides. Never a loan, never interest she didn't set."},
    "catalogue": {"label": "Catalogue & enquiries", "hi": "catalogue aur enquiry", "accounts": True, "money": False,
                  "screens": ["onboarding", "login", "home", "search", "catalogue", "product_detail", "enquiry", "wishlist", "gallery",
                              "store_info", "profile"],
                  "tabs": ["home", "catalogue", "wishlist", "profile"],
                  "flow": ["home", "catalogue", "product_detail", "enquiry"],
                  "words": ["catalogue", "catalog", "enquiry", "enquire", "inquiry", "designs", "collection", "browse", "products dikhana",
                            "price list", "brochure"],
                  "brief": "A beautiful browsable catalogue (photos, specs, her prices if she shows them) with one strong "
                           "action: enquire on WhatsApp / call with the item prefilled, or save to a wishlist."},
    "events": {"label": "Events & tickets", "hi": "event aur ticket", "accounts": True, "money": True,
               "screens": ["onboarding", "login", "home", "events", "event_detail", "pass", "gallery", "store_info", "notifications",
                           "profile"],
               "tabs": ["home", "events", "pass", "profile"],
               "flow": ["home", "events", "event_detail", "payment", "pass"],
               "words": ["event", "events", "ticket", "tickets", "program", "show", "utsav", "workshop", "registration", "entry pass",
                         "festival"],
               "brief": "Upcoming events with date, place and seats she gives; register or buy a pass (UPI), show the QR pass "
                        "at the gate, photos after the event."},
    "community": {"label": "Updates & community", "hi": "updates aur samaj", "accounts": False, "money": False,
                  "screens": ["onboarding", "home", "updates", "events", "event_detail", "gallery", "donate", "store_info",
                              "notifications", "profile", "support"],
                  "tabs": ["home", "updates", "events", "profile"],
                  "flow": ["home", "updates", "events", "event_detail", "donate"],
                  "words": ["updates", "news", "notice", "society", "community", "samaj", "temple", "mandir", "members", "trust",
                            "ngo", "darshan", "aarti"],
                  "brief": "News and notices from her organisation, timings, events and photos; donations only to her own "
                           "UPI ID with the registration details she gives. No account needed to read."},
}

# ---------------------------------------------------------------- 10 premium app design styles
def _st(label, fonts, moods, radius, nav, card, button, header, fab, trans, texture, motion, do, dont):
    return {"label": label, "fonts": fonts, "moods": moods, "radius": radius, "nav": nav, "card": card, "button": button,
            "header": header, "fab": fab, "transition": trans, "texture": texture, "motion": motion, "do": do, "dont": dont}


# 16 premium styles; each fixes a STRUCTURE (navigation, FAB, card, button, header, screen transition, texture) so the
# three looks she compares differ in structure, not only in colour. Any part can be changed later in her words.
STYLES: dict[str, dict[str, Any]] = {
    "clean_commerce": _st("Clean commerce", "jakarta_inter", ["bright"], 14, "bar", "elevated", "rounded", "search_bar", "extended",
                          "fade_through", "", ["m_stagger", "m_press", "m_badge", "m_shimmer", "m_pop"],
                          "product-first: crisp white surfaces, big product art, price in bold, sticky add-to-cart bar, delivery time chip",
                          "no decoration that slows shopping, no tiny prices, no more than one accent colour"),
    "aurora_glass": _st("Aurora glass", "outfit_inter", ["tech", "gradient", "dark"], 22, "floating_pill", "glass", "gradient", "large_title",
                        "regular", "container", "", ["m_glow", "m_tilt", "m_stagger", "m_glass_shine", "m_parallax"],
                        "soft aurora gradient background, frosted glass cards, floating pill tab bar, glowing primary buttons",
                        "no glass on glass on glass (keep text on solid enough surfaces), no low-contrast labels"),
    "soft_pastel": _st("Soft pastel", "sora_nunito", ["calm", "candy", "warm"], 26, "bar_labels", "filled", "pill", "greeting", "large",
                       "axis_y", "dots", ["m_pop", "m_float", "m_bounce", "m_stagger"],
                       "friendly and soft: pastel tinted cards, rounded everything, greeting header with her name, cute line icons",
                       "no harsh black blocks, no dense tables"),
    "bold_blocks": _st("Bold blocks", "space_dm", ["bold", "contrast"], 12, "bottom_app_bar", "block", "chunky", "big_type", "docked",
                       "push", "grid", ["m_pop", "m_count", "m_marquee", "m_press", "m_shake"],
                       "confident colour blocks, 2 px ink borders with offset shadows, huge numbers, chunky buttons, docked main button",
                       "no thin grey text, no pastel washes"),
    "luxury_noir": _st("Luxury noir", "cormorant_manrope", ["dark", "gold", "luxury"], 4, "drawer", "image_overlay", "square", "transparent",
                       "none", "zoom", "marble", ["m_blur_in", "m_ken_burns", "m_parallax", "m_draw"],
                       "dark canvas, gold hairlines, serif display titles, big imagery under scrims, side-bar menu, letter-spaced labels",
                       "no bright colours, no crowded screens, no bouncy motion"),
    "desi_festive": _st("Desi festive", "yatra_hind", ["festive", "warm"], 16, "drawer_bar", "filled", "rounded", "brand_bar", "extended",
                        "axis_x", "bandhani", ["m_swing", "m_sparkle", "m_stagger", "m_pop"],
                        "Indian celebration: maroon / marigold / gold, motif dividers Hoola draws, Devanagari display lines, bandhani texture",
                        "no religious symbols unless she asks, no copied artwork or logos"),
    "minimal_mono": _st("Minimal mono", "inter_inter", ["mono", "neutral"], 8, "top_tabs", "outlined", "square", "large_title", "small",
                        "axis_x", "", ["m_draw", "m_reveal", "m_press"],
                        "precision: black / white + one accent, thin dividers, numbered lists, top tabs, lots of air",
                        "no shadows, no gradients, no decoration"),
    "fresh_organic": _st("Fresh organic", "lora_dm", ["green", "earthy", "calm"], 24, "bar_labels", "filled", "pill", "greeting",
                         "extended", "axis_z", "leaf", ["m_morph", "m_float", "m_stagger", "m_breathe"],
                         "calm natural feel: greens, sand, clay; soft blob shapes drawn in SVG; leaf / grain details",
                         "no neon, no hard black boxes"),
    "trust_clinical": _st("Trust clinical", "manrope_inter", ["trust", "blue", "calm"], 12, "bar", "outlined", "rounded", "brand_bar",
                          "extended", "fade_through", "", ["m_stagger", "m_check", "m_progress", "m_press"],
                          "clear, calm, credible: blue / teal, big readable lists, registration numbers and timings visible",
                          "no playful stickers, no hype words, no medical claims"),
    "playful_pop": _st("Playful pop", "baloo_mukta", ["bright", "candy"], 22, "floating_pill", "filled", "chunky", "greeting", "speed_dial",
                       "zoom", "confetti", ["m_pop", "m_wiggle", "m_confetti", "m_jelly", "m_bounce"],
                       "fun and bright: colour blocks, stickers drawn in SVG, bouncy buttons, celebration on success",
                       "no dark heavy palettes, no long paragraphs"),
    "neo_soft": _st("Neo soft (neumorphic)", "quicksand_nunito", ["calm", "neutral"], 22, "bar_minimal", "neumorphic", "soft",
                    "center_title", "regular", "axis_z", "", ["m_press", "m_breathe", "m_pop", "m_progress"],
                    "soft 3D: surfaces pressed out of the background with light + dark shadows, round controls, calm colours",
                    "no thin text on soft shadows (contrast first), no busy pictures"),
    "mesh_gradient": _st("Mesh gradient", "unbounded_inter", ["tech", "gradient", "bright"], 24, "floating_pill", "mesh", "gradient",
                         "big_type", "large", "container", "grain", ["m_gradient", "m_tilt", "m_glow", "m_stagger"],
                         "vivid gradient-mesh cards with film grain, huge display type, tilting 3D cards, floating bar",
                         "no flat grey screens, never text straight on a busy gradient without a scrim"),
    "editorial_image": _st("Editorial image", "playfair_lato", ["luxury", "warm"], 6, "top_tabs", "image_overlay", "pill", "parallax_hero",
                           "none", "container", "paper", ["m_ken_burns", "m_parallax", "m_blur_in", "m_reveal"],
                           "magazine app: full-bleed art with parallax, serif headlines over scrims, top tabs, paper texture",
                           "no cluttered toolbars, no tiny art"),
    "enterprise_pro": _st("Enterprise pro", "plexsans_plexdeva", ["trust", "neutral", "blue"], 10, "drawer_bar", "outlined", "rounded",
                          "collapsing", "menu", "axis_x", "", ["m_chart_grow", "m_number_roll", "m_stagger", "m_progress"],
                          "dense but clear dashboards: KPI tiles, tables that become cards on phones, filters, side bar for every module",
                          "no decoration over data, no hidden actions"),
    "dark_neon": _st("Dark neon", "syne_inter", ["dark", "tech", "contrast"], 16, "floating_pill", "glass", "gradient", "large_title",
                     "regular", "zoom", "grid", ["m_glow", "m_pulse", "m_marquee", "m_tilt"],
                     "near-black canvas, neon accent glows, glass cards, grid texture, energetic motion (gyms, gaming, nightlife)",
                     "no long reading text, keep neon for accents only"),
    "paper_craft": _st("Paper craft", "kalam_mukta", ["warm", "earthy", "festive"], 18, "bar_labels", "stacked", "rounded", "greeting",
                       "extended", "curl", "paper", ["m_swing", "m_pop", "m_stagger"],
                       "hand-made Indian feel: stacked paper cards, handwritten headings, block-print accents, page-turn transitions",
                       "no glossy gradients, no corporate stock look"),
}

# ---------------------------------------------------------------- 51 screens x 6 designs (written by Opus) + 6 by code
SCREENS: dict[str, dict[str, Any]] = {
    "onboarding": {"label": "Welcome", "hi": "swagat", "why": "3 quick slides: what the app does for the customer", "data": ["business"],
                   "variants": ["three full-bleed illustrated slides with dots and a big 'Shuru karein' button",
                                "single screen: big illustration, 3 benefit rows with icons, primary + 'baad mein' text button",
                                "stacked cards that fan in, each a benefit, skip at top right",
                                "brand colour hero with logo, one-line promise, language chips (English / हिन्दी / मराठी)",
                                "split screen: top art, bottom sheet with benefits and the start button",
                                "minimal: logo, name, tagline, timings chip, two buttons (login / browse as guest)"]},
    "login": {"label": "Login (phone OTP)", "hi": "login", "why": "phone number -> OTP on WhatsApp / SMS; no password", "data": [],
              "variants": ["large title, +91 phone field, 'OTP bhejo' button, 6 OTP boxes appear below in the same screen",
                           "illustration top, rounded bottom sheet with phone field and WhatsApp OTP note",
                           "two-step card: phone, then OTP with resend timer and edit number link",
                           "minimal centered form with country chip, consent line, and a 'browse without login' link",
                           "brand gradient header, white card overlapping it with the phone field",
                           "full-screen keypad style: big digits of the number as typed, OTP boxes after"]},
    "home": {"label": "Home", "hi": "home", "why": "the one main action in the first screen", "data": ["business", "products", "offers"],
             "variants": ["search bar header, offer banner carousel, category circles row, 2-column best-sellers grid",
                          "greeting with her customer's name, big primary action card, horizontal rails (today / popular / new)",
                          "hero card with today's special and price, quick action chips, recent orders strip",
                          "dashboard tiles (2x2) for the main actions, notice banner, timings + open now chip",
                          "full-width brand banner with logo, sticky search, staggered category tiles, 'reorder' card",
                          "editorial: large title, one featured item with big art, then a numbered list of collections"]},
    "search": {"label": "Search", "hi": "khojo", "why": "find anything fast", "data": ["products"],
               "variants": ["search field focused, recent searches chips, popular items list with thumbnails",
                            "voice search mic button, trending tags, results as 2-column grid with filters chip row",
                            "results list with highlight of matched words, sort sheet, empty state illustration",
                            "category shortcuts while typing, instant results grouped by category",
                            "big search hero with suggestions in Hindi + English, recent items carousel",
                            "minimal list results with price right-aligned and add buttons"]},
    "categories": {"label": "Categories", "hi": "category", "why": "browse by type", "data": ["products"],
                   "variants": ["left rail of categories, right grid of sub-categories with art",
                                "2-column big category cards with art and item count",
                                "list with large thumbnails and chevrons, search at top",
                                "colourful tiles in a 3-column grid with icons",
                                "accordion sections with sub-items as chips",
                                "horizontal tabs on top, products below for the chosen category"]},
    "product_list": {"label": "Item list", "hi": "saamaan", "why": "items of one category with prices", "data": ["products"],
                     "variants": ["2-column grid cards: art, name, unit, price, ADD button turning into a +/- stepper",
                                  "list rows with thumbnail, name, price and stepper; sticky filter + sort bar",
                                  "large single-column cards with art and a short line",
                                  "compact list for big catalogues with price per unit and in-stock dot",
                                  "masonry grid with variable art heights",
                                  "chips for sub-categories at top, list below, floating cart bar with total"]},
    "product_detail": {"label": "Item detail", "hi": "saamaan ki jaankari", "why": "everything about one item + add to cart", "data": ["products"],
                       "variants": ["big art carousel, name, price, unit chips, description, sticky bottom bar with stepper + Add",
                                    "collapsing hero image, details sections (about, how to use, declarations), related items rail",
                                    "split: art left top, info card overlapping, size / weight chips, add button",
                                    "editorial: big serif name, price, long description, specs table",
                                    "compact sheet-style detail sliding up over the list",
                                    "gallery thumbnails row, highlights with icons, legal declarations (MRP, net qty, maker) collapsible"]},
    "cart": {"label": "Cart", "hi": "cart", "why": "review items, change quantity", "data": ["products"],
             "variants": ["item rows with steppers, bill summary card, sticky checkout bar with total",
                          "cards per item with remove swipe hint, coupon field, delivery or pickup toggle",
                          "minimal list and a big total, 'add more' link, save for later",
                          "grouped by category, savings shown, note-to-shop field",
                          "empty-state friendly illustration when nothing is in the cart + suggestions",
                          "compact bill with taxes line by line and the delivery charge she sets"]},
    "checkout": {"label": "Checkout", "hi": "checkout", "why": "address / pickup, time, payment method", "data": ["business"],
                 "variants": ["stepper (Address > Time > Pay) with cards, sticky place order bar",
                              "single page: address card with change, delivery slot chips, payment options, total",
                              "pickup or delivery segmented control, time chips, notes, summary",
                              "map preview card (static), address form, slot picker sheet",
                              "accordion sections that open one after another",
                              "minimal list of choices with radio rows and one big pay button"]},
    "payment": {"label": "Payment (UPI)", "hi": "payment", "why": "pay by UPI to her own UPI ID; no card details in the app", "data": ["business"],
                "variants": ["amount large, payee name, UPI app choices as text chips, 'Pay karein' button, secure note",
                             "QR card to scan from another phone + 'pay on this phone' button",
                             "bottom sheet over the order summary with UPI ID copy and pay buttons",
                             "step list: open UPI app > pay > come back; status chip waiting / paid",
                             "cash on delivery / pay at counter option next to UPI (if she allows)",
                             "minimal: amount, payee, one button, 'payment hua? Ho gaya / Nahi hua' follow-up"]},
    "order_success": {"label": "Order placed", "hi": "order ho gaya", "why": "confirmation and what happens next", "data": [],
                      "variants": ["big animated check, order number, ETA, track button",
                                   "confetti burst, summary card, share on WhatsApp button",
                                   "illustration of the shop packing, timeline preview",
                                   "minimal receipt card with print-like edges",
                                   "thank-you note from the shop owner, items list, support link",
                                   "next steps list (packing > out for delivery > delivered) with the current step lit"]},
    "orders": {"label": "My orders", "hi": "mere order", "why": "past and running orders", "data": ["orders"],
               "variants": ["segmented Running / Past, cards with status chip and reorder button",
                            "timeline list grouped by date",
                            "compact rows with item count, total, status dot",
                            "big card for the running order on top, history below",
                            "grid of order cards with first item art",
                            "list with filters (status, month) and invoice download"]},
    "order_track": {"label": "Track order", "hi": "order kahan hai", "why": "live status of one order", "data": ["orders"],
                    "variants": ["vertical status timeline with times, call shop button, items collapsed",
                                 "progress bar with 4 steps and a big current status line",
                                 "static map-style illustration with the route, ETA card",
                                 "card stack: status, delivery person (name only), items, bill",
                                 "minimal: current step huge, small steps below, help link",
                                 "chat-like status updates from the shop"]},
    "offers": {"label": "Offers", "hi": "offer", "why": "her current offers (only real ones)", "data": ["offers"],
               "variants": ["coupon cards with dashed edges and copy code buttons",
                            "big banner offers in a vertical list",
                            "grid of offer tiles with percent badges",
                            "festival offer hero + small offers below",
                            "list with validity dates and terms expandable",
                            "points / cashback style cards with progress"]},
    "wishlist": {"label": "Saved", "hi": "pasand", "why": "items saved for later", "data": ["products"],
                 "variants": ["2-column grid with heart toggles and enquire buttons",
                              "list with move-to-cart buttons", "collections (folders) of saved items",
                              "empty state with heart illustration", "large cards with notes", "compact rows with share button"]},
    "menu": {"label": "Menu", "hi": "menu", "why": "dishes by category with veg marks and prices", "data": ["products"],
             "variants": ["sticky category tabs, dish rows with veg mark, price, ADD button, floating cart bar",
                          "big photo cards per dish with description and options hint",
                          "two-level: category list then dishes, bestseller tags",
                          "menu-card look: serif titles, dotted price leaders, chef's special box",
                          "grid of dishes with art and quick add",
                          "search + filters (veg only, spicy, under price) and compact rows"]},
    "dish_detail": {"label": "Dish options", "hi": "dish", "why": "size / spice / extras before adding", "data": ["products"],
                    "variants": ["bottom sheet with size radio, spice level chips, extras checkboxes, add button with total",
                                 "full screen with big art, description, options cards",
                                 "stepper for quantity, note to kitchen field",
                                 "combo builder with sections",
                                 "minimal options list with price differences",
                                 "art top, nutrition / allergens collapsible (only what she gives)"]},
    "services": {"label": "Services", "hi": "sevaayein", "why": "what she offers, duration, price", "data": ["services"],
                 "variants": ["list cards with duration chip, price, Book button",
                              "category tabs and service rows with icons",
                              "grid of service tiles with art and starting price",
                              "packages / combos on top, single services below",
                              "accordion by category with short descriptions",
                              "minimal list with right-aligned prices and chevrons"]},
    "service_detail": {"label": "Service detail", "hi": "seva ki jaankari", "why": "what happens, how long, price", "data": ["services"],
                       "variants": ["hero art, duration + price chips, steps of the service, Book now bar",
                                    "what's included checklist, things to bring, FAQ",
                                    "before you come notes, staff who do it, book button",
                                    "compact card detail sheet", "editorial long description with highlights",
                                    "pricing options (basic / premium) as selectable cards"]},
    "staff": {"label": "Choose a person", "hi": "kaun karega", "why": "doctor / stylist / trainer if she has a team", "data": ["team"],
              "variants": ["avatar cards with name, role, languages, next free time",
                           "list with initials avatars and specialisation chips",
                           "carousel of team cards with 'any available' first",
                           "grid with availability dots", "minimal radio list", "profile-style cards with qualifications (only real ones)"]},
    "slot_picker": {"label": "Pick a time", "hi": "samay chuniye", "why": "free slots from her appointment book", "data": ["slots"],
                    "variants": ["horizontal date strip, morning / afternoon / evening slot chips, confirm bar",
                                 "calendar month view with available days, slots below",
                                 "list of next free slots with day names", "time wheel style picker",
                                 "week grid with free cells", "earliest available highlighted card + other times"]},
    "booking_confirm": {"label": "Confirm booking", "hi": "booking pakki", "why": "summary, pay or pay at visit", "data": ["slots"],
                        "variants": ["summary card (service, person, date, time, price), notes, confirm button",
                                     "ticket-style card with tear line", "steps done check list and add-to-calendar",
                                     "minimal confirmation sheet", "success state with reschedule / cancel buttons",
                                     "summary + payment choice (UPI now / at the counter)"]},
    "my_bookings": {"label": "My bookings", "hi": "meri booking", "why": "upcoming and past bookings", "data": ["bookings"],
                    "variants": ["Upcoming / Past tabs, cards with date block, reschedule and cancel",
                                 "timeline grouped by month", "big next booking card with countdown",
                                 "compact list with status chips", "calendar view with dots", "cards with directions and call buttons"]},
    "courses": {"label": "Courses / batches", "hi": "course", "why": "what students can join", "data": ["courses"],
                "variants": ["cards with subject colour, level, timings, seats left (only real)",
                             "list grouped by class / standard", "grid with icon per subject",
                             "featured batch hero + others", "tabs Online / Offline / Weekend", "minimal list with fee per month"]},
    "course_detail": {"label": "Course detail", "hi": "course jaankari", "why": "syllabus, teacher, timing, fees", "data": ["courses"],
                      "variants": ["header with subject art, chips (duration, mode), syllabus accordion, enroll bar",
                                   "teacher card, schedule table, fees card", "outcomes checklist and FAQ",
                                   "lessons list with lock / free icons", "compact detail sheet", "editorial long page with highlights"]},
    "lesson": {"label": "Lesson / notes", "hi": "lesson", "why": "study material inside the app", "data": ["courses"],
               "variants": ["video player area (placeholder art), notes below, next lesson button",
                            "reading view with large text and highlight", "PDF-like pages with page counter",
                            "audio lesson card with progress", "flash cards", "lesson list with progress rings"]},
    "quiz": {"label": "Test / quiz", "hi": "test", "why": "practice questions and score", "data": ["courses"],
             "variants": ["one question per screen, options as big cards, progress bar, timer",
                          "score result with ring and review list", "list of tests with best score",
                          "true / false quick quiz", "leaderboard (first names only)", "answer review with explanations"]},
    "timetable": {"label": "Timetable", "hi": "samay sarani", "why": "today and this week", "data": ["schedule"],
                  "variants": ["day strip and cards per class with time and room",
                               "week grid", "agenda list", "today hero card + next", "calendar month", "compact rows with teacher names"]},
    "fees": {"label": "Fees / dues", "hi": "fees", "why": "what is due and paid", "data": ["dues"],
             "variants": ["due card with amount, due date, pay button; paid history below",
                          "month chips and a ledger list", "installments timeline", "receipt list with download",
                          "minimal amount due hero", "family view (children) with dues each"]},
    "plans": {"label": "Plans", "hi": "plan", "why": "membership plans and prices she gives", "data": ["plans"],
              "variants": ["3 plan cards side scroll with the popular one highlighted",
                           "comparison table with ticks", "stacked cards with benefits", "toggle monthly / yearly",
                           "minimal list with prices", "premium dark card for the top plan"]},
    "member_card": {"label": "Member pass", "hi": "member card", "why": "QR pass to show at the counter", "data": ["member"],
                    "variants": ["wallet-style card with name, plan, valid till, big QR",
                                 "flip card front (photo initials) back (QR)", "full-screen QR with brightness note",
                                 "card + renew button + days left ring", "minimal pass with barcode", "ticket style pass"]},
    "checkin": {"label": "Check in", "hi": "check in", "why": "attendance at the centre", "data": ["member"],
                "variants": ["big check-in button with pulse, today's streak", "calendar of visits", "QR scan prompt",
                             "attendance percentage ring", "list of check-ins", "class check-in cards"]},
    "progress": {"label": "Progress", "hi": "pragati", "why": "results over time", "data": ["member"],
                 "variants": ["line chart drawn in SVG, stats tiles", "milestones timeline", "body / skill metrics cards",
                              "streak calendar", "before / after numbers (no photos without consent)", "goals checklist"]},
    "request_service": {"label": "Raise a request", "hi": "complaint / request", "why": "problem, photo, address, time", "data": ["services"],
                        "variants": ["problem type chips, description, add photo tile, preferred time chips, submit",
                                     "stepper: what > where > when", "big issue cards to pick from, then details",
                                     "minimal form with voice note button", "address card + slot chips + submit",
                                     "emergency banner + regular form"]},
    "job_status": {"label": "Request status", "hi": "kaam kahan tak", "why": "who is coming and when", "data": ["jobs"],
                   "variants": ["timeline (received > assigned > on the way > working > done)",
                                "technician card (name only) with ETA and call", "list of my requests with status chips",
                                "big current status hero", "chat-like updates", "map-style illustration card"]},
    "estimate": {"label": "Approve extra work", "hi": "extra kaam", "why": "line-by-line yes / no before work starts", "data": ["jobs"],
                 "variants": ["line items with yes / no toggles and a total that updates",
                              "cards per item with reason and price", "before photo + suggested work list",
                              "minimal list with approve all / pick", "comparison basic vs full fix", "sheet with lines and send button"]},
    "invoice": {"label": "Bill", "hi": "bill", "why": "the bill with every line", "data": ["bills"],
                "variants": ["receipt card with lines, taxes, total, pay and download buttons",
                             "minimal amount hero with breakdown below", "paper style bill with shop details",
                             "list of bills with paid / due chips", "bill + warranty card", "bill with UPI QR"]},
    "khata": {"label": "Khata", "hi": "khata", "why": "what the customer owes and paid", "data": ["dues"],
              "variants": ["balance hero (owe / advance), ledger rows with + / - colours, pay button",
                           "month groups with totals", "statement style table", "chart of the balance over months",
                           "minimal: big balance, last 5 entries", "family / shop accounts switcher"]},
    "rewards": {"label": "Points", "hi": "points", "why": "loyalty she decides", "data": ["rewards"],
                "variants": ["points ring, how to earn list, rewards to redeem cards",
                             "tier card (silver / gold) with progress", "stamp card (10 visits = 1 free)",
                             "history list", "scratch-card style reward reveal (no gambling)", "minimal points + redeem"]},
    "catalogue": {"label": "Catalogue", "hi": "catalogue", "why": "browse items to enquire", "data": ["products"],
                  "variants": ["filter chips, 2-column grid, enquire icon on each",
                               "big lookbook cards", "list with specs summary", "collections carousel + grid",
                               "masonry gallery of items", "table view for trade buyers (MOQ, rate)"]},
    "enquiry": {"label": "Enquire", "hi": "enquiry", "why": "send a question about an item", "data": ["business"],
                "variants": ["item summary, quantity, message, WhatsApp and call buttons",
                             "form card with name / phone / message", "quick chips (price? delivery? custom?) + send",
                             "minimal sheet with prefilled WhatsApp text", "callback request with time chips",
                             "visit-the-shop card with timings and directions"]},
    "events": {"label": "Events", "hi": "events", "why": "what's coming up", "data": ["events"],
               "variants": ["date-block cards with title, place, register button",
                            "featured event hero + list", "calendar strip and event rows", "grid of posters (drawn)",
                            "timeline by month", "minimal list with time and seats she gives"]},
    "event_detail": {"label": "Event detail", "hi": "event jaankari", "why": "when, where, who, register", "data": ["events"],
                     "variants": ["hero art, date / time / place rows, about, register bar",
                                  "schedule timeline for the day", "speakers / artists cards (only real)",
                                  "ticket types as selectable cards", "map-style place card", "FAQ and rules"]},
    "pass": {"label": "My pass", "hi": "pass", "why": "QR entry pass", "data": ["events"],
             "variants": ["ticket card with tear line and big QR", "wallet stack of passes", "full-screen QR",
                          "pass + add-to-calendar", "minimal pass list", "group pass with names"]},
    "gallery": {"label": "Photos", "hi": "photos", "why": "her photos (real ones only)", "data": ["photos"],
                "variants": ["masonry grid with lightbox", "albums grid", "full-width story-like carousel",
                             "3-column square grid", "featured photo + thumbnails", "timeline by event"]},
    "updates": {"label": "Updates", "hi": "suchna", "why": "news and notices from her", "data": ["updates"],
                "variants": ["feed cards with date, title, short text, pinned notice on top",
                             "list with category chips", "big image cards", "notice board style",
                             "timeline", "minimal headline list"]},
    "donate": {"label": "Donate", "hi": "daan", "why": "to her own UPI ID, with her registration details", "data": ["business"],
               "variants": ["amount chips, custom amount, purpose chips, pay by UPI, 80G line only if she has it",
                            "impact cards then donate button", "minimal UPI ID + QR card",
                            "monthly support toggle (reminder only, no auto debit)", "donation history", "thank-you screen"]},
    "store_info": {"label": "Shop info", "hi": "dukaan ki jaankari", "why": "address, timings, call, WhatsApp, directions", "data": ["business"],
                   "variants": ["map-style card (drawn), address, open-now chip, call / WhatsApp / directions buttons",
                                "timings table by day, holidays", "photo header + info rows",
                                "multiple branches list", "minimal contact card", "about the owner + since year (only real)"]},
    "notifications": {"label": "Notifications", "hi": "suchnaayein", "why": "order / booking / offer updates", "data": ["updates"],
                      "variants": ["grouped Today / Earlier with icons", "cards with action buttons", "minimal list with unread dots",
                                   "tabs Orders / Offers", "empty state", "settings link per type"]},
    "profile": {"label": "Profile", "hi": "profile", "why": "account, addresses, language, help, legal links", "data": [],
                "variants": ["avatar header with name / phone, settings rows with icons, legal links at the bottom",
                             "cards: my orders, addresses, language, notifications, help, privacy, delete account",
                             "minimal grouped list", "stats header (orders / points) + rows",
                             "dark header card", "language switcher prominent (English / हिन्दी / मराठी)"]},
    "support": {"label": "Help", "hi": "madad", "why": "FAQ, call, WhatsApp, grievance contact", "data": ["business"],
                "variants": ["FAQ accordion + contact buttons", "chat-style help entry (WhatsApp)", "issue categories grid",
                             "minimal call / WhatsApp / email rows", "order-specific help list", "grievance officer card (from seller details)"]},
}
CODE_SCREENS: dict[str, dict[str, str]] = {
    "splash": {"label": "Splash", "hi": "shuru", "why": "app icon and name while it opens (made by code)"},
    "consent": {"label": "Data consent", "hi": "sahmati", "why": "DPDP notice: what data, why, how to withdraw (made by code)"},
    "notify_permission": {"label": "Notifications ask", "hi": "suchna ki ijazat", "why": "explains why before Android / iOS asks (made by code)"},
    "seller_info": {"label": "Seller details", "hi": "vikreta jaankari", "why": "legal name, address, grievance officer (E-commerce Rules 2020; made by code)"},
    "privacy": {"label": "Privacy policy", "hi": "privacy", "why": "required by Google Play and the App Store (made by code)"},
    "delete_account": {"label": "Delete account", "hi": "account hatao", "why": "required in-app by both stores (made by code)"},
}

# ---------------------------------------------------------------- structures, motion (v0.128.1: the full design system)
from . import designsys as DS  # noqa: E402

NAV: dict[str, str] = {k: v["desc"] for k, v in DS.NAV.items()}
MOTION: dict[str, str] = {k: v["desc"] for k, v in DS.MOTION.items()}

# ---------------------------------------------------------------- industry defaults (40 industries of the field cards)
INDUSTRY: dict[str, dict[str, Any]] = {
    "food_shop": {"goal": "shop", "styles": ["desi_festive", "clean_commerce", "fresh_organic"]},
    "restaurant": {"goal": "food_order", "styles": ["clean_commerce", "luxury_noir", "bold_blocks"]},
    "food_maker": {"goal": "food_order", "styles": ["paper_craft", "desi_festive", "fresh_organic"]},
    "fashion": {"goal": "shop", "styles": ["luxury_noir", "editorial_image", "desi_festive"]},
    "electronics": {"goal": "shop", "styles": ["clean_commerce", "aurora_glass", "bold_blocks"]},
    "retail": {"goal": "shop", "styles": ["clean_commerce", "playful_pop", "bold_blocks"]},
    "clinic": {"goal": "booking", "styles": ["trust_clinical", "minimal_mono", "fresh_organic"]},
    "health_allied": {"goal": "booking", "styles": ["trust_clinical", "minimal_mono", "fresh_organic"]},
    "wellness": {"goal": "membership", "styles": ["dark_neon", "neo_soft", "fresh_organic"]},
    "beauty": {"goal": "booking", "styles": ["luxury_noir", "neo_soft", "soft_pastel"]},
    "school": {"goal": "learning", "styles": ["playful_pop", "trust_clinical", "soft_pastel"]},
    "coaching": {"goal": "learning", "styles": ["bold_blocks", "trust_clinical", "aurora_glass"]},
    "skills": {"goal": "learning", "styles": ["playful_pop", "soft_pastel", "minimal_mono"]},
    "home_services": {"goal": "service_request", "styles": ["bold_blocks", "trust_clinical", "clean_commerce"]},
    "repair": {"goal": "service_request", "styles": ["aurora_glass", "bold_blocks", "minimal_mono"]},
    "auto": {"goal": "booking", "styles": ["bold_blocks", "luxury_noir", "aurora_glass"]},
    "construction": {"goal": "catalogue", "styles": ["minimal_mono", "luxury_noir", "trust_clinical"]},
    "real_estate": {"goal": "catalogue", "styles": ["editorial_image", "luxury_noir", "trust_clinical"]},
    "finance": {"goal": "booking", "styles": ["trust_clinical", "minimal_mono", "luxury_noir"]},
    "legal": {"goal": "booking", "styles": ["minimal_mono", "trust_clinical", "luxury_noir"]},
    "travel": {"goal": "booking", "styles": ["bold_blocks", "fresh_organic", "playful_pop"]},
    "hospitality": {"goal": "booking", "styles": ["editorial_image", "luxury_noir", "fresh_organic"]},
    "events": {"goal": "catalogue", "styles": ["desi_festive", "luxury_noir", "soft_pastel"]},
    "creative": {"goal": "catalogue", "styles": ["mesh_gradient", "minimal_mono", "editorial_image"]},
    "it": {"goal": "service_request", "styles": ["enterprise_pro", "aurora_glass", "mesh_gradient"]},
    "telecom": {"goal": "service_request", "styles": ["enterprise_pro", "aurora_glass", "bold_blocks"]},
    "manufacturing": {"goal": "catalogue", "styles": ["enterprise_pro", "trust_clinical", "minimal_mono"]},
    "agriculture": {"goal": "shop", "styles": ["fresh_organic", "desi_festive", "clean_commerce"]},
    "logistics": {"goal": "service_request", "styles": ["enterprise_pro", "bold_blocks", "trust_clinical"]},
    "trade": {"goal": "khata", "styles": ["trust_clinical", "bold_blocks", "minimal_mono"]},
    "ngo": {"goal": "community", "styles": ["fresh_organic", "soft_pastel", "minimal_mono"]},
    "spiritual": {"goal": "community", "styles": ["desi_festive", "minimal_mono", "soft_pastel"]},
    "personal": {"goal": "catalogue", "styles": ["minimal_mono", "luxury_noir", "bold_blocks"]},
    "pets": {"goal": "booking", "styles": ["playful_pop", "soft_pastel", "fresh_organic"]},
    "kids": {"goal": "learning", "styles": ["playful_pop", "soft_pastel", "fresh_organic"]},
    "staffing": {"goal": "service_request", "styles": ["enterprise_pro", "trust_clinical", "bold_blocks"]},
    "citizen_services": {"goal": "service_request", "styles": ["trust_clinical", "minimal_mono", "clean_commerce"]},
    "crafts": {"goal": "shop", "styles": ["paper_craft", "editorial_image", "desi_festive"]},
    "sports": {"goal": "membership", "styles": ["dark_neon", "bold_blocks", "playful_pop"]},
    "local_services": {"goal": "khata", "styles": ["soft_pastel", "playful_pop", "clean_commerce"]},
}
# a field card's website goal -> the app goal that fits it (used when the field has its own goal)
SITE_GOAL_TO_APP = {"booking": "booking", "menu_order": "food_order", "catalogue": "shop", "admissions": "learning",
                    "event": "events", "cause": "community", "info": "community", "portfolio": "catalogue"}

# ---------------------------------------------------------------- store + India rules (feed the plan, the prompts and the checks)
STORE_RULES: dict[str, str] = {
    "fssai": "Food: FSSAI licence number on the shop info and seller screens; veg / non-veg marks; no health-cure claims.",
    "nmc": "Clinic: factual info only (no 'best doctor', no cures, no patient testimonials); every medical screen says it does not "
           "replace a doctor's advice (Apple 1.4.1); on the App Store the clinic itself submits from its own organisation account "
           "(Apple 5.1.1(ix)); no diagnosis features; appointment data only.",
    "dci": "Dentist: factual info only, registration number shown; no 'painless guaranteed'.",
    "dmr": "No claims to cure or treat listed diseases (Drugs & Magic Remedies Act).",
    "pcpndt": "Ultrasound / diagnostics: state that sex determination is not done.",
    "pharmacy": "Pharmacy: no ordering or delivery of prescription medicines in the app; drug licence number shown.",
    "loans": "NO lending features (no loan applications, EMIs offered by the app, interest calculators that promise approval): "
             "Google Play's personal-loan rules in India need RBI-listed lenders. Info and appointments only.",
    "sebi": "Investments: no tips, no assured returns; SEBI registration / ARN shown; the business itself must submit to the App Store (5.1.1(ix)).",
    "irdai": "Insurance: licence number and insurer name; no guaranteed-return claims; no selling policies inside the app.",
    "icai": "CA firm: factual details only; no fee comparisons or superiority claims.",
    "bci": "Advocates: no advertising or soliciting (Bar Council Rule 36): name, enrolment, practice areas and appointments only, with a "
           "no-solicitation note; no client testimonials or success claims.",
    "rera": "Real estate: RERA registration number on every project screen; no possession dates or returns she can't prove.",
    "edu": "Education: no guaranteed ranks; if students are under 18, parental consent before an account (DPDP) and no ads / "
           "tracking; Google Play Families policy applies if children are the audience.",
    "astro": "Astrology / spiritual: no guaranteed results, no fear-based or cure claims.",
    "ngo": "NGO: registration (Trust / Society / Section 8), 12A / 80G / FCRA only if she has them; donations only to her own UPI ID.",
    "travel": "Travel: prices 'from', inclusions / exclusions, cancellation terms she gives; no fake scarcity.",
    "legal_metrology": "Packaged goods: MRP incl. taxes, net quantity, maker / packer, country of origin, consumer care on the item screen.",
    "hiring": "Placement: no fees from job seekers unless legal and stated; real openings only.",
    "govt_lookalike": "Near-government services: 'private service, not a government office' on the home screen; no emblems, no look-alike.",
    "vet": "Veterinary: VCI registration; no cure guarantees.",
    "gym": "Fitness: no guaranteed weight loss, no before / after photos without written consent.",
}
GENERAL_RULES = [
    "Physical goods and real-world services are paid by UPI to her own UPI ID (or cash / at the counter): Apple 3.1.3(e) and "
    "Google Play allow this; card numbers, CVV or UPI PIN are NEVER typed inside the app.",
    "Digital content sold inside the app (recorded courses, e-books, paid features) needs Google Play Billing / Apple in-app "
    "purchase: keep such content free inside the app or sell it outside the app.",
    "Every app has: a privacy policy screen + link, in-app 'delete my account' (if accounts exist), a consent notice before "
    "collecting data (DPDP), an explanation before asking for notification permission, seller details with a grievance "
    "officer when it sells anything (Consumer Protection E-Commerce Rules 2020).",
    "Login by phone OTP only (no social logins) so Apple 4.8 needs no extra sign-in option; never ask for a password.",
    "Each app is unique to this business (its own content, data, branding and features) - never a reskin of another app (Apple 4.3, Play spam policy).",
    "No brand logos of other companies, no national emblem or flag, no religious symbol unless she asks; UPI app names only as text.",
    "Never invent prices, phone numbers, addresses, timings, team names, degrees, ratings, reviews or counts: [blank] instead.",
]
# screens that are code-made in every app of a goal (order of appearance in the plan)
def code_screens_for(goal: str) -> list[str]:
    g = GOALS[goal]
    out = ["splash"]
    if g["accounts"]:
        out.append("consent")
    out.append("notify_permission")
    if g["money"]:
        out.append("seller_info")
    out.append("privacy")
    if g["accounts"]:
        out.append("delete_account")
    return out


def check() -> list[str]:
    """Library consistency (tests): every screen a goal uses exists, 6 designs each, 300+ designs, fonts / palettes known."""
    from ..site import taxonomy as ST
    problems: list[str] = []
    for gid, g in GOALS.items():
        for s in g["screens"] + g["tabs"] + g["flow"]:
            if s not in SCREENS:
                problems.append(f"goal {gid}: unknown screen {s}")
        for t in g["tabs"]:
            if t not in g["screens"]:
                problems.append(f"goal {gid}: tab {t} not a screen")
        if not 3 <= len(g["tabs"]) <= 5:
            problems.append(f"goal {gid}: {len(g['tabs'])} tabs")
    for sid, s in SCREENS.items():
        if len(s["variants"]) != 6:
            problems.append(f"screen {sid}: {len(s['variants'])} designs")
    from . import colors as CL
    from . import fonts as FN
    pairs = FN.pairs()
    for k, st in STYLES.items():
        if st["fonts"] not in pairs:
            problems.append(f"style {k}: font pair {st['fonts']}")
        for key, table in (("nav", DS.NAV), ("card", DS.CARDS), ("button", DS.BUTTONS), ("header", DS.HEADERS), ("fab", DS.FAB)):
            if st[key] not in table:
                problems.append(f"style {k}: {key} {st[key]}")
        if st["transition"] not in {v["web"] for v in DS.MOTION.values() if v["kind"] == "transition"}:
            problems.append(f"style {k}: transition {st['transition']}")
        if st["texture"] and st["texture"] not in DS.TEXTURES:
            problems.append(f"style {k}: texture {st['texture']}")
        for m in st["motion"]:
            if m not in MOTION:
                problems.append(f"style {k}: motion {m}")
        if not any(set(st["moods"]) & set(p["moods"]) for p in CL.palettes().values()):
            problems.append(f"style {k}: no palette for moods")
    for ind, v in INDUSTRY.items():
        if ind not in ST.INDUSTRIES:
            problems.append(f"industry {ind} unknown")
        if v["goal"] not in GOALS or any(s not in STYLES for s in v["styles"]):
            problems.append(f"industry {ind}: bad defaults")
    for ind in ST.INDUSTRIES:
        if ind not in INDUSTRY:
            problems.append(f"industry {ind} has no app defaults")
    if len(MOTION) != 100:
        problems.append(f"{len(MOTION)} motion presets")
    problems += DS.check()
    return problems
