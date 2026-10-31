"""v0.121 The website library's fixed parts: goals, design styles, pages, section designs, hero types, motion presets,
palettes, font pairs, industries and profession rules. Field cards (1,000 trades) live in `libdata/fields_*.txt`;
`library.py` composes 1,000 fields x 10 goals x 10 styles = 1,00,000 ready briefs from these.

Everything here is a starting point for the model (Opus adapts it to her business); nothing is copied whole into a site.
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------- site goals (10)
GOALS: dict[str, dict[str, Any]] = {
    "enquiry": {"label": "Calls / enquiries", "hi": "call aur enquiry", "cta": "call",
                "pages": ["services", "contact"], "sections": ["services_grid", "reviews", "cta_band", "contact_block"],
                "words": ["enquiry", "call", "contact", "leads", "customer", "grahak", "puchh"],
                "brief": "Every page pushes one clear action: call or WhatsApp. Phone number visible in the first screen, sticky call button on mobile, short enquiry form."},
    "booking": {"label": "Bookings / appointments", "hi": "booking", "cta": "booking",
                "pages": ["services", "booking", "contact"], "sections": ["services_grid", "booking_slots", "faq", "map_hours"],
                "words": ["booking", "appointment", "slot", "book", "reserve", "time"],
                "brief": "The site exists to fill her calendar: 'Book a slot' in the hero, services with duration and price (only her prices), live free slots from Hoola's booking book, timings and location."},
    "catalogue": {"label": "Product catalogue", "hi": "saamaan ki list", "cta": "whatsapp",
                  "pages": ["products", "about", "contact"], "sections": ["products_grid", "features_split", "reviews", "cta_band"],
                  "words": ["product", "catalogue", "catalog", "items", "saamaan", "maal", "rate", "price list", "shop", "dukaan"],
                  "brief": "Show what she sells with photos, names and (only if she gives them) prices; each product has an 'Order on WhatsApp' button with the item prefilled. No checkout in this version."},
    "menu_order": {"label": "Menu + orders", "hi": "menu aur order", "cta": "order",
                   "pages": ["menu", "about", "contact"], "sections": ["menu_list", "gallery_masonry", "map_hours", "cta_band"],
                   "words": ["menu", "order", "food", "khana", "delivery", "thali", "parcel"],
                   "brief": "A menu that reads well on a phone: categories, veg / non-veg marks, her prices, today's special; order by WhatsApp or call; delivery areas and timings."},
    "portfolio": {"label": "Portfolio / work", "hi": "kaam dikhana", "cta": "enquiry",
                  "pages": ["portfolio", "about", "contact"], "sections": ["portfolio_grid", "process_steps", "reviews", "cta_band"],
                  "words": ["portfolio", "work", "kaam", "projects", "photos", "gallery", "designs"],
                  "brief": "Her best work first, large and fast; each project with a short story (what, where, result); process; enquiry form asking what they need."},
    "admissions": {"label": "Admissions / leads", "hi": "admission", "cta": "enquiry",
                   "pages": ["courses", "admissions", "about", "contact"], "sections": ["courses_list", "results_toppers", "faq", "cta_band"],
                   "words": ["admission", "course", "class", "batch", "students", "coaching", "school", "fees"],
                   "brief": "Courses / batches with timings, fees only if she gives them, faculty, real results only with her proof, admission enquiry form and a parents' FAQ."},
    "event": {"label": "Event / launch", "hi": "event", "cta": "enquiry",
              "pages": ["events", "contact"], "sections": ["hero", "timeline_history", "faq", "cta_band"],
              "words": ["event", "launch", "opening", "wedding", "function", "programme", "sale", "utsav"],
              "brief": "One date, one place, one action: countdown, schedule, venue map, RSVP / enquiry; after the date it turns into a 'what happened' gallery."},
    "personal": {"label": "Personal brand", "hi": "apni pehchaan", "cta": "enquiry",
                 "pages": ["about", "services", "contact"], "sections": ["intro_story", "stats_counters", "reviews", "contact_block"],
                 "words": ["personal", "profile", "portfolio", "khud", "my name", "resume", "freelancer", "coach"],
                 "brief": "The person is the product: a real photo, her story in her words, what she offers, proof (only real), how to reach her."},
    "cause": {"label": "NGO / cause", "hi": "seva / sanstha", "cta": "donate",
              "pages": ["about", "projects", "donate", "contact"], "sections": ["donate_impact", "projects_case", "certificates_trust", "cta_band"],
              "words": ["ngo", "trust", "foundation", "donation", "daan", "seva", "charity", "sanstha", "mandal"],
              "brief": "Mission, work on the ground with real photos, impact numbers only from her, registration details (12A / 80G only if she has them), how to help or donate (her UPI ID / bank details she gives)."},
    "info": {"label": "Information / directory", "hi": "jaankari", "cta": "contact",
             "pages": ["about", "faq", "blog", "contact"], "sections": ["features_split", "faq", "blog_list", "contact_block"],
             "words": ["information", "jaankari", "details", "directory", "list", "guide", "blog"],
             "brief": "Clear, searchable information: what, who, where, how; FAQ; updates / blog; contact. Fast and plain beats flashy here."},
}

# ---------------------------------------------------------------- design styles (10)
STYLES: dict[str, dict[str, Any]] = {
    "editorial_calm": {"label": "Editorial calm", "fonts": "fraunces_inter", "moods": ["calm", "earthy"],
                       "radius": 4, "grid": "asymmetric 12-column, generous white space, large serif headlines",
                       "motion": ["reveal-fade-soft", "split-words-soft", "image-zoom-slow", "underline-draw"],
                       "heroes": ["editorial_split", "big_type", "photo_caption"],
                       "do": "magazine feel: big serif headings, small caps labels, thin rules, real photos with captions",
                       "dont": "no gradients, no bouncy motion, no stock-looking icons"},
    "bold_modern": {"label": "Bold modern", "fonts": "space_dm", "moods": ["bold", "contrast"],
                    "radius": 14, "grid": "strong blocks, oversized type, full-bleed colour bands",
                    "motion": ["split-chars-strong", "reveal-up-strong", "marquee-fast", "magnetic-buttons", "count-up"],
                    "heroes": ["kinetic_type", "full_bleed_photo", "marquee_hero"],
                    "do": "huge confident headlines, one loud accent colour, chunky buttons, marquee strip",
                    "dont": "no thin pastel text, no clutter"},
    "warm_local": {"label": "Warm local", "fonts": "baloo_mukta", "moods": ["warm", "festive"],
                   "radius": 18, "grid": "friendly rounded cards, hand-drawn style dividers, photos of the real place",
                   "motion": ["reveal-up-soft", "float-gentle", "stagger-cards", "wave-divider"],
                   "heroes": ["shopfront_photo", "photo_stack", "illustrated_scene"],
                   "do": "feels like the neighbourhood shop: warm colours, rounded shapes, Hindi / Marathi lines, owner's photo",
                   "dont": "no cold corporate blues, no stiff stock people"},
    "luxury_dark": {"label": "Luxury dark", "fonts": "cormorant_manrope", "moods": ["dark", "gold"],
                    "radius": 2, "grid": "dark canvas, wide margins, slow reveals, gold hairlines",
                    "motion": ["reveal-blur-slow", "parallax-soft", "image-zoom-slow", "line-draw-gold"],
                    "heroes": ["video_loop", "full_bleed_photo", "spotlight_product"],
                    "do": "restraint: few words, big images, thin gold lines, letter-spaced labels",
                    "dont": "no bright colours, no crowded sections, no fast motion"},
    "playful_bright": {"label": "Playful bright", "fonts": "sora_nunito", "moods": ["bright", "candy"],
                       "radius": 24, "grid": "bouncy cards, stickers, tilted elements, colour blocks",
                       "motion": ["pop-in", "wiggle-hover", "float-gentle", "stagger-cards", "confetti-cta"],
                       "heroes": ["illustrated_scene", "sticker_collage", "kinetic_type"],
                       "do": "fun for kids / youth / food: bright blocks, playful shapes, emoji-free illustrations",
                       "dont": "no dark heavy palettes, no long paragraphs"},
    "minimal_swiss": {"label": "Minimal Swiss", "fonts": "inter_inter", "moods": ["mono", "neutral"],
                      "radius": 0, "grid": "strict grid, black / white + one colour, lots of air",
                      "motion": ["reveal-fade-soft", "line-draw", "sticky-progress"],
                      "heroes": ["big_type", "grid_index", "editorial_split"],
                      "do": "precision: aligned grid, numbered sections, one accent colour",
                      "dont": "no shadows, no rounded blobs, no decoration"},
    "festive_traditional": {"label": "Festive traditional", "fonts": "yatra_hind", "moods": ["festive", "warm"],
                            "radius": 12, "grid": "ornamental borders drawn by Hoola, rangoli / toran motifs, rich colours",
                            "motion": ["reveal-scale-soft", "float-gentle", "sparkle", "toran-swing"],
                            "heroes": ["ornament_frame", "photo_stack", "shopfront_photo"],
                            "do": "Indian celebration feel: maroon / marigold / gold, Devanagari display type, motifs Hoola draws",
                            "dont": "no religious symbols unless she asks, no copied artwork"},
    "tech_gradient": {"label": "Tech gradient", "fonts": "jakarta_inter", "moods": ["tech", "gradient"],
                      "radius": 16, "grid": "glass cards, gradient glows, product shots, dark or light",
                      "motion": ["reveal-up-strong", "tilt-cards", "glow-follow", "count-up", "gradient-shift"],
                      "heroes": ["gradient_glow", "device_mockup", "3d_object"],
                      "do": "modern SaaS / ISP / IT look: gradient glows, crisp icons, numbers that count up",
                      "dont": "no clip-art, no heavy textures"},
    "organic_natural": {"label": "Organic natural", "fonts": "lora_dm", "moods": ["green", "earthy"],
                        "radius": 28, "grid": "soft blobs, leaf / grain textures drawn in SVG, earthy photos",
                        "motion": ["reveal-up-soft", "blob-morph", "parallax-soft", "float-gentle"],
                        "heroes": ["full_bleed_photo", "blob_photo", "illustrated_scene"],
                        "do": "calm and natural: greens, sand, clay; rounded blobs; wellness, farm, organic food",
                        "dont": "no neon, no hard edges everywhere"},
    "corporate_trust": {"label": "Corporate trust", "fonts": "manrope_inter", "moods": ["trust", "blue"],
                        "radius": 8, "grid": "clean columns, certificates, numbers, clear navigation",
                        "motion": ["reveal-up-soft", "count-up", "stagger-cards", "logos-marquee"],
                        "heroes": ["split_photo", "stats_hero", "full_bleed_photo"],
                        "do": "serious and credible: navy / teal, certificates and registration numbers, team, process",
                        "dont": "no playful stickers, no slang in headings"},
}

# ---------------------------------------------------------------- pages
PAGES: dict[str, dict[str, str]] = {
    "home": {"en": "Home", "hi": "मुख्य पृष्ठ", "why": "first impression + the one main action"},
    "about": {"en": "About", "hi": "हमारे बारे में", "why": "who, since when, why trust us (her own story)"},
    "services": {"en": "Services", "hi": "सेवाएँ", "why": "what she does, for whom, how"},
    "products": {"en": "Products", "hi": "उत्पाद", "why": "what she sells, with photos"},
    "menu": {"en": "Menu", "hi": "मेन्यू", "why": "dishes, categories, veg marks, her prices"},
    "gallery": {"en": "Gallery", "hi": "फ़ोटो गैलरी", "why": "real photos of the place / work"},
    "pricing": {"en": "Pricing", "hi": "दाम", "why": "her packages (only her figures)"},
    "booking": {"en": "Book", "hi": "बुकिंग", "why": "choose a slot / request a booking"},
    "contact": {"en": "Contact", "hi": "संपर्क", "why": "phone, WhatsApp, address, map, hours, form"},
    "faq": {"en": "FAQ", "hi": "सवाल-जवाब", "why": "answers customers keep asking"},
    "team": {"en": "Team", "hi": "हमारी टीम", "why": "people behind the business"},
    "courses": {"en": "Courses", "hi": "कोर्स", "why": "batches, timings, fees she gives"},
    "admissions": {"en": "Admissions", "hi": "प्रवेश", "why": "how to join, documents, dates"},
    "portfolio": {"en": "Work", "hi": "हमारा काम", "why": "best projects first"},
    "projects": {"en": "Projects", "hi": "परियोजनाएँ", "why": "case stories with photos"},
    "reviews": {"en": "Reviews", "hi": "ग्राहकों की राय", "why": "real reviews she provides"},
    "blog": {"en": "Blog", "hi": "लेख", "why": "updates, tips (Kalam)"},
    "offers": {"en": "Offers", "hi": "ऑफ़र", "why": "current offers with end dates"},
    "events": {"en": "Event", "hi": "कार्यक्रम", "why": "date, place, schedule, RSVP"},
    "donate": {"en": "Support us", "hi": "सहयोग करें", "why": "how to help, her UPI / bank details"},
    "careers": {"en": "Careers", "hi": "नौकरी", "why": "open roles she lists"},
    "coverage": {"en": "Areas we serve", "hi": "सेवा क्षेत्र", "why": "localities / pincodes served"},
    "privacy": {"en": "Privacy policy", "hi": "गोपनीयता नीति", "why": "required: what the forms collect and why"},
    "terms": {"en": "Terms", "hi": "नियम व शर्तें", "why": "terms of use / sale"},
    "refund": {"en": "Refund policy", "hi": "रिफ़ंड नीति", "why": "required when she sells"},
    "disclaimer": {"en": "Disclaimer", "hi": "अस्वीकरण", "why": "required for some professions (lawyers, finance)"},
}

# ---------------------------------------------------------------- section designs: 30 types x 10 variants = 300 (before / after lives in gallery)
SECTIONS: dict[str, dict[str, Any]] = {
    "hero": {"label": "Hero", "variants": [
        "split: headline + action left, large real photo right with soft shape behind",
        "full-bleed photo with dark gradient overlay, headline bottom-left",
        "kinetic type only: huge headline animating word by word, one button",
        "centered headline with a slow marquee of services under it",
        "short muted video loop behind the headline (poster image first)",
        "editorial: big serif headline, small caption, photo offset into the next section",
        "product spotlight: one product image floating on a colour field with a soft shadow",
        "stacked photos fanned out like prints, headline beside them",
        "stats hero: headline + three real numbers counting up",
        "illustrated scene drawn in SVG (shopfront, street, desk) with gentle motion"]},
    "intro_story": {"label": "Story / about", "variants": [
        "owner photo + her story in her words, signature line",
        "timeline strip of years with one line each (only her dates)",
        "two columns: why we started / what we promise",
        "pull quote in large type with photo of the place",
        "three short paragraphs with small images between",
        "values as four icon cards",
        "before-and-now photo pair with a short line",
        "map of where they started with a line drawn to today",
        "video interview thumbnail with a play button (her video only)",
        "letter style note from the owner"]},
    "services_grid": {"label": "Services", "variants": [
        "3-column cards with icon, name, one line, 'Puchhiye' link",
        "list with large numbers 01, 02, 03 and hover reveal",
        "tabs per service category",
        "alternating image / text rows",
        "accordion with details and price (only hers)",
        "bento grid: one big card + small cards",
        "horizontal scroll cards on mobile, grid on desktop",
        "icon strip + detail panel that changes on tap",
        "cards with a photo background and overlay text",
        "comparison of two service levels"]},
    "products_grid": {"label": "Products", "variants": [
        "photo grid with name, price (if given), 'WhatsApp par order' button",
        "category chips that filter the grid",
        "large featured product + grid below",
        "carousel of bestsellers + full grid",
        "list view with small photos for many items",
        "masonry of product photos with hover detail",
        "product cards with variant chips (size / colour) she lists",
        "'new arrivals' strip + catalogue",
        "lookbook: lifestyle photos with product tags",
        "price-list table for wholesale (only her rates)"]},
    "menu_list": {"label": "Menu", "variants": [
        "categories with dotted leader lines to prices",
        "cards with dish photo, veg / non-veg mark, price",
        "tabs: breakfast / lunch / dinner",
        "today's special highlight + full menu",
        "thali builder style list (items she offers)",
        "two-column printed-menu look",
        "chips filter: veg, jain, spicy",
        "combo / family pack cards",
        "drinks & desserts strip",
        "PDF-like menu board with chalk style"]},
    "gallery_masonry": {"label": "Gallery", "variants": [
        "masonry grid with lightbox",
        "horizontal film strip with snap",
        "before / after slider pairs",
        "full-width slideshow with captions",
        "polaroid collage",
        "grid with category filter",
        "one big + four small layout",
        "video + photo mix",
        "Instagram-style square grid (her photos, no embed)",
        "scroll-driven zoom gallery"]},
    "process_steps": {"label": "How it works", "variants": [
        "numbered steps with a line that draws on scroll", "horizontal steps with icons", "vertical timeline",
        "sticky left title, steps scroll on the right", "cards that flip", "circular flow", "zig-zag path",
        "step tabs", "checklist style", "video per step (her videos)"]},
    "stats_counters": {"label": "Numbers", "variants": [
        "four counters counting up", "big single number with context", "numbers on a colour band",
        "numbers with small icons", "number + chart bar", "numbers inside rings", "ticker strip",
        "year founded + customers + areas", "numbers over a photo", "numbers in a bento grid"]},
    "reviews": {"label": "Reviews (real only)", "variants": [
        "quote cards with name and area", "single large rotating quote", "Google rating summary she gives + quotes",
        "masonry of short reviews", "video testimonials (her files)", "marquee of short lines",
        "review + photo of the job", "star summary + 3 quotes", "WhatsApp-screenshot style cards (text retyped, consented)",
        "case quote with result"]},
    "pricing_table": {"label": "Pricing", "variants": [
        "three plan cards, middle highlighted", "simple price list table", "toggle monthly / yearly",
        "package cards with included items", "single price with what's included", "per-service prices in accordion",
        "comparison table", "starting-from prices with 'call for quote'", "bundle builder list", "offer price with end date"]},
    "faq": {"label": "FAQ", "variants": [
        "accordion", "two-column accordion", "search box + accordion", "category tabs", "chat-bubble style Q&A",
        "top 5 + 'more on WhatsApp'", "cards", "numbered list", "FAQ with schema markup", "voice-friendly short answers"]},
    "team": {"label": "Team", "variants": [
        "photo cards with role", "founder spotlight + team grid", "hover reveals a line", "carousel",
        "circle photos row", "team with qualifications (real)", "department groups", "single founder note",
        "team at work photos", "timeline of who joined when"]},
    "timeline_history": {"label": "Timeline / schedule", "variants": [
        "vertical timeline", "horizontal scroll timeline", "event schedule by time", "milestones with photos",
        "year chips", "agenda tabs per day", "countdown + schedule", "progress line that fills on scroll",
        "map + timeline", "minimal list"]},
    "features_split": {"label": "Feature rows", "variants": [
        "image left / text right alternating", "sticky image with changing text", "icon list beside a photo",
        "feature with device mockup", "three columns with illustrations", "big number + feature", "checklist beside photo",
        "video beside text", "tabs with images", "feature cards with hover lift"]},
    "cta_band": {"label": "Call to action band", "variants": [
        "full-width colour band with one button", "split: text + call / WhatsApp buttons", "floating card over photo",
        "marquee band with button", "offer countdown band", "gradient band with glow", "QR code + phone",
        "minimal line + arrow", "form inline (name, phone)", "festival themed band"]},
    "contact_block": {"label": "Contact", "variants": [
        "phone, WhatsApp, email cards + form", "map left, details right", "big phone number + buttons",
        "form with service choice", "branch list", "hours table + map", "contact with photo of the shop",
        "minimal contact line", "QR to WhatsApp + address", "contact steps (call / visit / message)"]},
    "map_hours": {"label": "Map + hours", "variants": [
        "map link card + hours table", "address with landmark + directions button", "hours with 'open now' badge",
        "multiple branches tabs", "map image (static) + Google Maps link", "parking / landmark notes",
        "hours + holiday notice", "delivery radius note", "how to reach (bus / metro)", "minimal hours line"]},
    "booking_slots": {"label": "Booking", "variants": [
        "next free slots as chips (from Hoola booking)", "service picker then slots", "calendar strip",
        "request form with preferred time", "doctor / staff picker", "WhatsApp booking button", "slot list per day",
        "booking steps explained", "group booking request", "home-visit request with area"]},
    "courses_list": {"label": "Courses", "variants": [
        "course cards with duration and batch time", "tabs per class / standard", "table of batches",
        "course detail accordion", "featured course + list", "online / offline chips", "syllabus timeline",
        "faculty per course", "demo-class button", "fees on request"]},
    "results_toppers": {"label": "Results (real only)", "variants": [
        "student cards with marks she provides", "year-wise results table", "marquee of selections",
        "big number + list", "photo wall (with consent)", "rank list", "testimonial + result", "subject toppers",
        "selection letters list", "results by batch"]},
    "portfolio_grid": {"label": "Portfolio", "variants": [
        "large project tiles", "masonry with filters", "case cards with result line", "full-width project slides",
        "hover reveal titles", "list with thumbnails", "before / after projects", "video reel + grid",
        "client-type tabs", "one featured case study"]},
    "projects_case": {"label": "Case stories", "variants": [
        "problem / work / result", "photo story", "timeline of the project", "numbers + quote", "map of locations",
        "gallery + short note", "impact cards", "beneficiary story (consented)", "progress bars (her numbers)", "press mentions she gives"]},
    "offers_banner": {"label": "Offers", "variants": [
        "top bar strip", "card with end date", "festival banner", "coupon style", "countdown",
        "combo offer cards", "first-visit offer", "seasonal sale grid", "referral offer", "minimal offer line"]},
    "logos_marquee": {"label": "Clients / partners (real only)", "variants": [
        "logo marquee (logos she provides with permission)", "names as text marquee", "grid of names", "sectors served",
        "certifications row", "trusted-by line", "partner cards", "brands we stock (names as text)", "awards she has", "press names she gives"]},
    "video_showcase": {"label": "Video", "variants": [
        "click-to-play video with poster (loads only on tap)", "video + text", "vertical reel style", "video gallery",
        "background muted loop", "YouTube link card (opens YouTube)", "how-to videos list", "testimonial video",
        "factory / kitchen tour", "event highlights"]},
    "blog_list": {"label": "Blog / updates", "variants": [
        "cards with date", "featured + list", "tips list", "news ticker", "category tabs", "minimal list",
        "magazine grid", "FAQ-style articles", "monthly updates", "notice board"]},
    "certificates_trust": {"label": "Trust / registrations", "variants": [
        "registration numbers list (GST, FSSAI, RERA... only real)", "certificate images", "awards row", "years + customers",
        "insurance / license badges as text", "safety promises", "guarantee terms she gives", "memberships", "inspection reports", "bank / payment modes accepted"]},
    "coverage_areas": {"label": "Areas served", "variants": [
        "locality chips", "pincode list", "map with areas (static)", "city cards", "searchable area list",
        "delivery radius line", "branch + area tabs", "route list", "coming-soon areas", "areas table"]},
    "donate_impact": {"label": "Donate / impact", "variants": [
        "impact numbers + donate button", "UPI QR she gives", "bank details card", "volunteer form",
        "project needs list", "monthly giving note", "story + ask", "transparency report link", "80G note (only if real)", "in-kind donation list"]},
    "whatsapp_float": {"label": "WhatsApp / call float", "variants": [
        "round WhatsApp button bottom-right", "call + WhatsApp pair on mobile", "sticky bottom bar", "pill with text",
        "appears after scroll", "only on mobile", "with office hours note", "with prefilled message", "minimal icon", "expanded on first visit"]},
}

# ---------------------------------------------------------------- hero types (24)
HEROES: dict[str, str] = {
    "editorial_split": "serif headline left, photo right, caption",
    "big_type": "oversized headline filling the screen",
    "photo_caption": "large photo with a magazine caption",
    "kinetic_type": "headline letters / words animate in",
    "full_bleed_photo": "edge-to-edge photo with overlay text",
    "marquee_hero": "headline + moving strip of words",
    "shopfront_photo": "the real shop / place photo, warm overlay",
    "photo_stack": "fanned photo prints",
    "illustrated_scene": "SVG illustration drawn by Hoola",
    "video_loop": "muted short loop with poster image",
    "spotlight_product": "one product on a colour field",
    "sticker_collage": "playful cut-outs and stickers",
    "grid_index": "numbered index of sections as the hero",
    "ornament_frame": "festive border drawn by Hoola",
    "gradient_glow": "soft gradient glow behind the headline",
    "device_mockup": "phone / laptop frame with her screenshot",
    "3d_object": "light 3D shape (three.js) after first paint",
    "blob_photo": "photo inside an organic blob shape",
    "split_photo": "half photo, half text",
    "stats_hero": "headline + counting numbers",
    "map_hero": "stylised map of her area",
    "form_hero": "headline + short enquiry form",
    "before_after_hero": "before / after slider as the hero",
    "menu_hero": "dish photo + today's special",
}

# ---------------------------------------------------------------- motion: 12 effects x 5 intensities = 60 presets
MOTION_EFFECTS: dict[str, str] = {
    "reveal": "fade + move into place when the element enters the screen",
    "stagger": "children reveal one after another",
    "split": "headline split into words / letters that rise in",
    "count": "numbers count up from 0 to her value",
    "draw": "SVG lines / underlines draw themselves",
    "parallax": "layer moves slower than the page",
    "marquee": "endless horizontal strip of words / logos",
    "magnetic": "buttons lean toward the finger / cursor",
    "tilt": "cards tilt slightly with pointer",
    "zoom": "image slowly zooms while in view",
    "float": "gentle up-down floating of a shape",
    "progress": "a line fills as the section scrolls",
}
MOTION_LEVELS = {"soft": (0.6, 12), "calm": (0.8, 18), "medium": (0.7, 28), "strong": (0.55, 44), "slow": (1.4, 20)}
MOTION_PRESETS: dict[str, dict[str, Any]] = {
    f"{e}-{lvl}": {"effect": e, "level": lvl, "duration": d, "distance": dist, "say": MOTION_EFFECTS[e]}
    for e in MOTION_EFFECTS for lvl, (d, dist) in MOTION_LEVELS.items()}
# names used by the styles (aliases onto the 60)
MOTION_ALIASES = {
    "reveal-fade-soft": "reveal-soft", "reveal-up-soft": "reveal-calm", "reveal-up-strong": "reveal-strong",
    "reveal-blur-slow": "reveal-slow", "reveal-scale-soft": "reveal-soft", "split-words-soft": "split-calm",
    "split-chars-strong": "split-strong", "image-zoom-slow": "zoom-slow", "underline-draw": "draw-calm",
    "line-draw": "draw-soft", "line-draw-gold": "draw-slow", "marquee-fast": "marquee-strong", "logos-marquee": "marquee-calm",
    "magnetic-buttons": "magnetic-medium", "count-up": "count-medium", "float-gentle": "float-soft",
    "stagger-cards": "stagger-medium", "wave-divider": "draw-calm", "parallax-soft": "parallax-soft",
    "pop-in": "reveal-strong", "wiggle-hover": "tilt-strong", "confetti-cta": "float-strong", "sticky-progress": "progress-calm",
    "sparkle": "float-calm", "toran-swing": "float-slow", "tilt-cards": "tilt-medium", "glow-follow": "magnetic-soft",
    "gradient-shift": "float-slow", "blob-morph": "float-slow"}


def motion_preset(name: str) -> dict[str, Any]:
    return MOTION_PRESETS.get(MOTION_ALIASES.get(name, name)) or MOTION_PRESETS["reveal-calm"]


# ---------------------------------------------------------------- palettes (50): bg, surface, ink, primary, accent + moods
PALETTES: dict[str, dict[str, Any]] = {}
_PAL = """
paper_ink|calm,neutral,mono|#FAF7F2|#FFFFFF|#1B1A17|#1B1A17|#C2410C
sand_terracotta|earthy,warm|#F6EFE6|#FFFBF5|#2B211B|#B4532A|#E9A23B
sage_clay|green,earthy,calm|#F3F5EF|#FFFFFF|#1F2A22|#4F6F52|#C8775A
midnight_gold|dark,gold,luxury|#0E0E10|#17171B|#F2EDE4|#C9A45C|#E8D3A2
ink_lime|bold,contrast,tech|#0B0C0E|#16181C|#F5F7F2|#C6F432|#5B8CFF
cream_maroon|festive,warm|#FFF8EE|#FFFFFF|#2A1414|#7A1E2C|#E3A21A
marigold_teal|festive,bright|#FFF7E8|#FFFFFF|#1E2328|#E8890C|#0F766E
royal_blue_trust|trust,blue|#F5F8FC|#FFFFFF|#0F1B2D|#1D4ED8|#0EA5E9
navy_teal|trust,blue,calm|#F4F7F8|#FFFFFF|#0B2233|#0B4F6C|#16A39A
forest_cream|green,calm|#F7F4EC|#FFFFFF|#14221A|#1F5135|#D4A373
candy_pop|bright,candy|#FFF6FB|#FFFFFF|#24122E|#FF4F9A|#3D7BFF
sunny_play|bright,candy|#FFFBEA|#FFFFFF|#1F1B2E|#FFB703|#3A86FF
mono_red|mono,bold,contrast|#FFFFFF|#F4F4F4|#111111|#111111|#E63946
graphite_orange|bold,contrast|#F2F2F0|#FFFFFF|#1C1C1C|#FF5A1F|#1C1C1C
violet_glow|tech,gradient|#0D0B1E|#16132D|#EEEAFE|#7C5CFF|#22D3EE
ocean_gradient|tech,gradient,blue|#F4F8FF|#FFFFFF|#0A1A33|#2563EB|#06B6D4
rose_gold|luxury,warm|#FBF6F4|#FFFFFF|#2C1E1E|#B76E79|#D4AF37
olive_brass|earthy,luxury|#F5F3EA|#FFFFFF|#262618|#5B5B2E|#B08D57
chilli_cream|warm,bold,food|#FFF6EF|#FFFFFF|#2B1510|#D7263D|#F4A259
saffron_green|festive,warm|#FFF9F0|#FFFFFF|#1E2016|#F28C28|#2E7D32
mint_fresh|green,bright,calm|#F2FBF7|#FFFFFF|#10261E|#10B981|#F59E0B
lavender_calm|calm,neutral|#F7F5FC|#FFFFFF|#221D33|#6D5BD0|#E7A9C0
charcoal_neon|dark,tech,contrast|#121212|#1C1C1C|#F1F1F1|#00E5A8|#FF3D7F
blush_minimal|calm,neutral|#FFF7F5|#FFFFFF|#2B2324|#C25B5B|#2B2324
denim_rust|neutral,earthy|#F3F5F8|#FFFFFF|#1A2230|#33507A|#C1592E
kesar_milk|warm,festive,food|#FFFBF2|#FFFFFF|#2D2416|#D97706|#9A3412
peacock|festive,luxury|#F2F8F8|#FFFFFF|#0D2424|#006D77|#E29578
tea_garden|green,earthy|#F4F6EE|#FFFFFF|#1D2617|#3C6E47|#B5651D
steel_safety|trust,contrast|#F3F4F6|#FFFFFF|#111827|#374151|#F59E0B
clinic_clean|trust,calm,blue|#F5FAFB|#FFFFFF|#0E2A33|#0E7490|#22C55E
school_bright|bright,trust|#F8FAFF|#FFFFFF|#14213D|#2B59C3|#FCA311
legal_ink|trust,mono|#F7F6F2|#FFFFFF|#1A1A1A|#22313F|#A67C52
finance_green|trust,green|#F4F8F5|#FFFFFF|#102318|#166534|#CA8A04
realty_slate|trust,neutral|#F4F5F7|#FFFFFF|#1E232B|#3B4A5E|#C08B5C
spa_stone|calm,earthy|#F5F2EE|#FFFFFF|#2A2622|#8A7968|#A3B18A
gym_volt|bold,dark,contrast|#0F1012|#1A1C20|#F4F4F4|#D7FF3A|#FF4D2E
bakery_cocoa|warm,food|#FFF8F1|#FFFFFF|#2E1B12|#7B3F00|#E8B04B
dairy_sky|calm,bright|#F4FAFF|#FFFFFF|#13263A|#3B82F6|#FBBF24
farm_soil|earthy,green|#F6F1E7|#FFFFFF|#2A2117|#6B4F2A|#6A994E
kids_rainbow|bright,candy|#FFFDF5|#FFFFFF|#1F2937|#EF476F|#118AB2
wedding_blush|festive,luxury,warm|#FFF7F3|#FFFFFF|#3A2228|#9D2A4B|#D4A24C
pooja_vermilion|festive,warm|#FFF8F0|#FFFFFF|#2B1A12|#C1121F|#F4A300
night_market|dark,festive|#14111C|#1F1A2B|#F7F1E8|#FF7A00|#FFD166
ivory_emerald|luxury,green|#FBF9F3|#FFFFFF|#13241D|#065F46|#B8860B
ice_cyan|tech,calm|#F5FBFD|#FFFFFF|#0B2530|#0891B2|#6366F1
sunset_coral|warm,bright|#FFF5F0|#FFFFFF|#2D1B1B|#F25F4C|#FFB347
stone_mono|mono,neutral|#EFEFEC|#F8F8F6|#151515|#151515|#7A7A72
indigo_ochre|neutral,festive|#F5F4FA|#FFFFFF|#1B1A33|#3730A3|#D69E2E
hospital_mint|trust,calm,green|#F3FBF8|#FFFFFF|#0F2A22|#0F766E|#38BDF8
craft_indigo|earthy,festive|#F6F3EC|#FFFFFF|#1C1B2E|#2E3A87|#C9732D
"""
for _line in _PAL.strip().splitlines():
    _n, _m, _bg, _sf, _ink, _p, _a = _line.split("|")
    PALETTES[_n] = {"moods": _m.split(","), "bg": _bg, "surface": _sf, "ink": _ink, "primary": _p, "accent": _a}

# ---------------------------------------------------------------- font pairs (30). Files: assets/fonts/<family-id>-<weight>.woff2
# (open licence fonts bundled with the site; families without a bundled file fall back to Poppins / Mukta).
FONTS: dict[str, dict[str, Any]] = {
    "fraunces_inter": {"head": "Fraunces", "body": "Inter", "deva": "Tiro Devanagari Hindi"},
    "space_dm": {"head": "Space Grotesk", "body": "DM Sans", "deva": "Mukta"},
    "baloo_mukta": {"head": "Baloo 2", "body": "Mukta", "deva": "Baloo 2"},
    "cormorant_manrope": {"head": "Cormorant Garamond", "body": "Manrope", "deva": "Martel"},
    "sora_nunito": {"head": "Sora", "body": "Nunito", "deva": "Baloo 2"},
    "inter_inter": {"head": "Inter", "body": "Inter", "deva": "Mukta"},
    "yatra_hind": {"head": "Yatra One", "body": "Hind", "deva": "Yatra One"},
    "jakarta_inter": {"head": "Plus Jakarta Sans", "body": "Inter", "deva": "Mukta"},
    "lora_dm": {"head": "Lora", "body": "DM Sans", "deva": "Martel"},
    "manrope_inter": {"head": "Manrope", "body": "Inter", "deva": "Mukta"},
    "playfair_lato": {"head": "Playfair Display", "body": "Lato", "deva": "Martel"},
    "poppins_mukta": {"head": "Poppins", "body": "Mukta", "deva": "Mukta"},
    "outfit_inter": {"head": "Outfit", "body": "Inter", "deva": "Mukta"},
    "syne_inter": {"head": "Syne", "body": "Inter", "deva": "Mukta"},
    "bricolage_inter": {"head": "Bricolage Grotesque", "body": "Inter", "deva": "Mukta"},
    "instrument_inter": {"head": "Instrument Serif", "body": "Inter", "deva": "Tiro Devanagari Hindi"},
    "rozha_hind": {"head": "Rozha One", "body": "Hind", "deva": "Rozha One"},
    "teko_hind": {"head": "Teko", "body": "Hind", "deva": "Teko"},
    "khand_mukta": {"head": "Khand", "body": "Mukta", "deva": "Khand"},
    "martel_mukta": {"head": "Martel", "body": "Mukta", "deva": "Martel"},
    "eczar_hind": {"head": "Eczar", "body": "Hind", "deva": "Eczar"},
    "laila_mukta": {"head": "Laila", "body": "Mukta", "deva": "Laila"},
    "dmserif_dm": {"head": "DM Serif Display", "body": "DM Sans", "deva": "Martel"},
    "archivo_inter": {"head": "Archivo", "body": "Inter", "deva": "Mukta"},
    "urbanist_mukta": {"head": "Urbanist", "body": "Mukta", "deva": "Mukta"},
    "nunito_hind": {"head": "Nunito", "body": "Hind", "deva": "Hind"},
    "josefin_lato": {"head": "Josefin Sans", "body": "Lato", "deva": "Mukta"},
    "spectral_inter": {"head": "Spectral", "body": "Inter", "deva": "Martel"},
    "kalam_mukta": {"head": "Kalam", "body": "Mukta", "deva": "Kalam"},
    "palanquin_hind": {"head": "Palanquin Dark", "body": "Palanquin", "deva": "Palanquin"},
}

# ---------------------------------------------------------------- profession / product rules (feed the checks)
LEGAL: dict[str, str] = {
    "fssai": "Food business: show the FSSAI licence / registration number she gives; veg / non-veg marks on dishes; no health-cure claims.",
    "nmc": "Doctor / clinic (NMC conduct rules): factual information only (name, qualifications, registration number, services, timings); no 'best doctor', no cure or guaranteed results, no patient testimonials about cures, no before / after of patients without written consent.",
    "dci": "Dentist (DCI rules): factual information only; no 'painless guaranteed', no comparative claims, registration number shown.",
    "bci": "Advocate / law firm (Bar Council of India Rule 36): no advertising or soliciting; only name, contact, enrolment, qualifications and practice areas; a 'no solicitation' disclaimer page that visitors accept; no client testimonials, no success-rate claims.",
    "icai": "Chartered accountant (ICAI website guidelines): factual details of the firm, partners and services; no client names without consent, no fee comparisons or claims of superiority.",
    "sebi": "Investments: advice only by a SEBI-registered adviser (show the number); mutual fund distributor shows ARN and the standard market-risk line; no guaranteed or assured returns.",
    "irdai": "Insurance: agent / broker licence number and insurer name; no 'guaranteed returns' unless the policy guarantees them; benefit examples only from the brochure.",
    "rera": "Real estate: MahaRERA / state RERA registration number on every project and agent page; no possession dates or returns she can't prove.",
    "loans": "Loans (RBI): name the lender(s) she works with; no 'guaranteed approval', no 'zero document' claims; interest only as the lender states.",
    "dmr": "Drugs & Magic Remedies Act: no claims to cure / treat listed diseases (diabetes, cancer, obesity, etc.) for any product or remedy.",
    "pcpndt": "Diagnostics with ultrasound: must state that sex determination is not done (PCPNDT Act).",
    "pharmacy": "Pharmacy: no online sale / delivery of prescription medicines through the site; show drug licence number; 'medicines on valid prescription only'.",
    "edu": "Education: no guaranteed ranks / selections; results only with her proof and student consent; fees only as she states.",
    "astro": "Astrology / spiritual: no guaranteed results, no fear-based claims, no cure claims (ASCI / DMR).",
    "ngo": "NGO: registration (Trust / Society / Section 8), 12A / 80G / FCRA only if she has them, with numbers; donation use explained.",
    "travel": "Travel: prices 'from', what is included / excluded, cancellation terms she gives; no fake 'last 2 seats'.",
    "legal_metrology": "Packaged goods with prices: MRP inclusive of taxes, net quantity, maker / packer, country of origin, consumer care (Legal Metrology e-commerce rules).",
    "hiring": "Placement / staffing: no fee from job seekers unless legally allowed and stated; real openings only.",
    "govt_lookalike": "Services near government work: say clearly 'private service, not a government office'; no government emblems, no look-alike of official portals.",
    "vet": "Veterinary: VCI registration; no cure guarantees.",
    "gym": "Fitness: no guaranteed weight loss in N days, no before / after without consent, no supplement cure claims.",
}

# ---------------------------------------------------------------- 40 industries (defaults for their field cards)
INDUSTRIES: dict[str, dict[str, Any]] = {
    "food_shop": {"label": "Food shops", "goal": "catalogue", "pages": ["home", "products", "about", "contact"],
                  "sections": ["hero", "products_grid", "intro_story", "reviews", "map_hours", "whatsapp_float"],
                  "trust": ["since year", "fresh daily", "hygiene", "FSSAI number"], "cta": "whatsapp",
                  "moods": ["warm", "food", "festive"], "photos": ["counter with products", "close-up of items", "owner at the shop"],
                  "questions": ["Dukaan ka naam aur area?", "Kaun se items sabse zyada bikte hain (daam ke saath, agar dikhane hain)?", "Home delivery karte ho? Kahan tak?"],
                  "legal": ["fssai"], "styles": ["warm_local", "festive_traditional", "organic_natural"]},
    "restaurant": {"label": "Restaurants & cafes", "goal": "menu_order", "pages": ["home", "menu", "gallery", "about", "contact"],
                   "sections": ["hero", "menu_list", "gallery_masonry", "reviews", "map_hours", "whatsapp_float"],
                   "trust": ["chef / family recipe", "hygiene", "FSSAI number", "ratings she gives"], "cta": "order",
                   "moods": ["warm", "food", "dark"], "photos": ["signature dishes", "the dining space", "kitchen team"],
                   "questions": ["Menu ki photo ya list bhejiye (daam ke saath)?", "Dine-in, takeaway, delivery - kya kya?", "Timings aur band ka din?"],
                   "legal": ["fssai"], "styles": ["warm_local", "luxury_dark", "bold_modern"]},
    "food_maker": {"label": "Caterers, tiffin & food makers", "goal": "enquiry", "pages": ["home", "menu", "about", "gallery", "contact"],
                   "sections": ["hero", "menu_list", "process_steps", "gallery_masonry", "reviews", "cta_band"],
                   "trust": ["events served (her number)", "hygiene", "FSSAI number"], "cta": "whatsapp",
                   "moods": ["warm", "food"], "photos": ["spread of dishes", "packing", "event setup"],
                   "questions": ["Kaun si service: tiffin, party order, wedding catering?", "Minimum order / per plate rate (agar dikhana hai)?", "Kaun se area cover karte ho?"],
                   "legal": ["fssai"], "styles": ["warm_local", "festive_traditional", "organic_natural"]},
    "fashion": {"label": "Fashion & clothing", "goal": "catalogue", "pages": ["home", "products", "gallery", "about", "contact"],
                "sections": ["hero", "products_grid", "gallery_masonry", "reviews", "cta_band", "whatsapp_float"],
                "trust": ["fabric / quality", "custom fitting", "exchange policy she gives"], "cta": "whatsapp",
                "moods": ["luxury", "warm", "festive"], "photos": ["collection on models / mannequins", "fabric close-ups", "store"],
                "questions": ["Kis tarah ke kapde: saree, suits, kids, men?", "Online order WhatsApp par lete ho?", "Exchange / return ka niyam?"],
                "legal": ["legal_metrology"], "styles": ["luxury_dark", "editorial_calm", "festive_traditional"]},
    "electronics": {"label": "Electronics & home goods", "goal": "catalogue", "pages": ["home", "products", "services", "contact"],
                    "sections": ["hero", "products_grid", "features_split", "certificates_trust", "map_hours", "whatsapp_float"],
                    "trust": ["authorised dealer (only if true)", "warranty support", "EMI options she offers"], "cta": "whatsapp",
                    "moods": ["tech", "trust"], "photos": ["showroom", "product range", "service desk"],
                    "questions": ["Kaun se brands rakhte ho (sirf naam, logo nahi)?", "Service / installation dete ho?", "EMI / exchange offer?"],
                    "legal": ["legal_metrology"], "styles": ["tech_gradient", "bold_modern", "corporate_trust"]},
    "retail": {"label": "General retail", "goal": "catalogue", "pages": ["home", "products", "about", "contact"],
               "sections": ["hero", "products_grid", "offers_banner", "intro_story", "map_hours", "whatsapp_float"],
               "trust": ["years in the area", "wide range", "fair prices"], "cta": "whatsapp",
               "moods": ["bright", "warm"], "photos": ["shelves", "counter", "owner"],
               "questions": ["Dukaan mein kya kya milta hai?", "Delivery karte ho?", "Timings?"],
               "legal": ["legal_metrology"], "styles": ["warm_local", "playful_bright", "bold_modern"]},
    "clinic": {"label": "Doctors & clinics", "goal": "booking", "pages": ["home", "services", "about", "booking", "contact"],
               "sections": ["hero", "services_grid", "team", "booking_slots", "faq", "map_hours"],
               "trust": ["qualifications", "registration number", "years of practice"], "cta": "booking",
               "moods": ["trust", "calm", "blue"], "photos": ["doctor (real)", "clinic interior", "reception"],
               "questions": ["Doctor ka naam, degree aur registration number?", "OPD timings aur fees (agar dikhani hai)?", "Appointment kaise lete ho?"],
               "legal": ["nmc"], "styles": ["corporate_trust", "editorial_calm", "organic_natural"]},
    "health_allied": {"label": "Diagnostics, pharmacy & allied health", "goal": "booking", "pages": ["home", "services", "about", "booking", "contact"],
                      "sections": ["hero", "services_grid", "process_steps", "certificates_trust", "map_hours", "whatsapp_float"],
                      "trust": ["accreditation (only real)", "trained staff", "home collection"], "cta": "booking",
                      "moods": ["trust", "calm", "green"], "photos": ["lab / store", "equipment", "staff"],
                      "questions": ["Kaun si services / tests?", "Home visit / collection?", "Licence / registration number?"],
                      "legal": ["nmc", "dmr"], "styles": ["corporate_trust", "minimal_swiss", "organic_natural"]},
    "wellness": {"label": "Fitness & wellness", "goal": "booking", "pages": ["home", "services", "pricing", "about", "contact"],
                 "sections": ["hero", "services_grid", "pricing_table", "team", "reviews", "cta_band"],
                 "trust": ["certified trainers", "equipment", "members (her number)"], "cta": "booking",
                 "moods": ["bold", "dark", "calm"], "photos": ["space", "classes in action", "trainers"],
                 "questions": ["Kaun si classes / programs?", "Membership plans (daam agar dikhane hain)?", "Timings aur free trial?"],
                 "legal": ["gym", "dmr"], "styles": ["bold_modern", "organic_natural", "luxury_dark"]},
    "beauty": {"label": "Beauty & grooming", "goal": "booking", "pages": ["home", "services", "gallery", "pricing", "contact"],
               "sections": ["hero", "services_grid", "gallery_masonry", "pricing_table", "reviews", "booking_slots"],
               "trust": ["trained artists", "hygiene", "products used"], "cta": "booking",
               "moods": ["luxury", "warm", "calm"], "photos": ["salon interior", "work results (consented)", "artists"],
               "questions": ["Services aur rate list?", "Home service bhi dete ho?", "Bridal packages?"],
               "legal": ["dmr"], "styles": ["luxury_dark", "editorial_calm", "playful_bright"]},
    "school": {"label": "Schools & preschools", "goal": "admissions", "pages": ["home", "about", "courses", "admissions", "gallery", "contact"],
               "sections": ["hero", "intro_story", "courses_list", "gallery_masonry", "faq", "cta_band"],
               "trust": ["board affiliation (real)", "safe campus", "teachers"], "cta": "enquiry",
               "moods": ["bright", "trust"], "photos": ["campus", "classrooms", "activities"],
               "questions": ["Board aur classes (Nursery se kitne tak)?", "Admission kab khulte hain, kya documents?", "Transport / facilities?"],
               "legal": ["edu"], "styles": ["playful_bright", "corporate_trust", "warm_local"]},
    "coaching": {"label": "Coaching & tuition", "goal": "admissions", "pages": ["home", "courses", "about", "admissions", "contact"],
                 "sections": ["hero", "courses_list", "results_toppers", "team", "faq", "cta_band"],
                 "trust": ["faculty experience", "results (with proof)", "batch size"], "cta": "enquiry",
                 "moods": ["trust", "bright", "bold"], "photos": ["classroom", "faculty", "students (consented)"],
                 "questions": ["Kaun se courses / exams / classes?", "Batch timings aur fees (agar dikhani hai)?", "Results jo dikhane hain (proof ke saath)?"],
                 "legal": ["edu"], "styles": ["bold_modern", "corporate_trust", "tech_gradient"]},
    "skills": {"label": "Skill, arts & hobby classes", "goal": "admissions", "pages": ["home", "courses", "gallery", "about", "contact"],
               "sections": ["hero", "courses_list", "gallery_masonry", "team", "reviews", "cta_band"],
               "trust": ["teacher's training", "performances / certificates", "small batches"], "cta": "enquiry",
               "moods": ["bright", "warm", "candy"], "photos": ["class in action", "performances", "teacher"],
               "questions": ["Kaun si class (music, dance, computer, driving...)?", "Batches aur fees?", "Online bhi?"],
               "legal": ["edu"], "styles": ["playful_bright", "warm_local", "editorial_calm"]},
    "home_services": {"label": "Home services", "goal": "enquiry", "pages": ["home", "services", "coverage", "contact"],
                      "sections": ["hero", "services_grid", "process_steps", "coverage_areas", "reviews", "whatsapp_float"],
                      "trust": ["verified technicians", "same-day visit (if true)", "work warranty she gives"], "cta": "call",
                      "moods": ["trust", "bold"], "photos": ["technician at work", "tools / van", "finished job"],
                      "questions": ["Kaun si services?", "Kaun se area / pincodes?", "Visiting charge aur timings?"],
                      "legal": [], "styles": ["bold_modern", "corporate_trust", "warm_local"]},
    "repair": {"label": "Repair services", "goal": "enquiry", "pages": ["home", "services", "about", "contact"],
               "sections": ["hero", "services_grid", "process_steps", "reviews", "map_hours", "whatsapp_float"],
               "trust": ["genuine parts (if true)", "warranty on repair", "years"], "cta": "whatsapp",
               "moods": ["tech", "bold"], "photos": ["repair bench", "shop", "fixed devices"],
               "questions": ["Kya kya repair karte ho?", "Pickup / home visit?", "Repair warranty?"],
               "legal": [], "styles": ["tech_gradient", "bold_modern", "minimal_swiss"]},
    "auto": {"label": "Automobile", "goal": "booking", "pages": ["home", "services", "about", "contact"],
             "sections": ["hero", "services_grid", "pricing_table", "reviews", "map_hours", "booking_slots"],
             "trust": ["trained mechanics", "genuine parts (if true)", "pickup-drop"], "cta": "booking",
             "moods": ["bold", "dark", "contrast"], "photos": ["workshop", "vehicles", "team"],
             "questions": ["Kaun si gaadiyan (2-wheeler, car, truck)?", "Services aur rates?", "Pickup-drop?"],
             "legal": [], "styles": ["bold_modern", "luxury_dark", "tech_gradient"]},
    "construction": {"label": "Construction & design", "goal": "portfolio", "pages": ["home", "portfolio", "services", "about", "contact"],
                     "sections": ["hero", "portfolio_grid", "process_steps", "services_grid", "reviews", "cta_band"],
                     "trust": ["projects done (her number)", "licences", "on-time record"], "cta": "enquiry",
                     "moods": ["earthy", "neutral", "trust"], "photos": ["completed projects", "site work", "drawings"],
                     "questions": ["Kis tarah ka kaam: ghar, commercial, interior?", "Best 5 projects ki photos?", "Kaun se shehar?"],
                     "legal": [], "styles": ["minimal_swiss", "editorial_calm", "corporate_trust"]},
    "real_estate": {"label": "Real estate", "goal": "enquiry", "pages": ["home", "projects", "about", "contact"],
                    "sections": ["hero", "projects_case", "features_split", "map_hours", "certificates_trust", "cta_band"],
                    "trust": ["RERA number", "projects delivered", "clear titles"], "cta": "call",
                    "moods": ["trust", "luxury", "neutral"], "photos": ["project exteriors", "sample flat", "location"],
                    "questions": ["Projects aur RERA number?", "Flat types aur daam (agar dikhane hain)?", "Site visit kaise?"],
                    "legal": ["rera"], "styles": ["luxury_dark", "corporate_trust", "editorial_calm"]},
    "finance": {"label": "Finance professionals", "goal": "enquiry", "pages": ["home", "services", "about", "faq", "contact", "disclaimer"],
                "sections": ["hero", "services_grid", "process_steps", "certificates_trust", "faq", "contact_block"],
                "trust": ["registration / licence numbers", "years", "confidentiality"], "cta": "call",
                "moods": ["trust", "green", "blue"], "photos": ["office", "professional (real)", "meeting room"],
                "questions": ["Kaun si services (GST, ITR, audit, insurance, loans)?", "Registration / licence number?", "Office timings?"],
                "legal": ["icai", "sebi", "irdai", "loans"], "styles": ["corporate_trust", "minimal_swiss", "editorial_calm"]},
    "legal": {"label": "Legal professionals", "goal": "info", "pages": ["home", "about", "services", "contact", "disclaimer"],
              "sections": ["hero", "intro_story", "services_grid", "team", "contact_block"],
              "trust": ["enrolment number", "courts / practice areas", "qualifications"], "cta": "contact",
              "moods": ["trust", "mono"], "photos": ["chamber / office", "advocate (real)"],
              "questions": ["Naam, enrolment number aur Bar Council?", "Practice areas aur courts?", "Office address aur timings?"],
              "legal": ["bci"], "styles": ["minimal_swiss", "editorial_calm", "corporate_trust"]},
    "travel": {"label": "Travel & transport", "goal": "enquiry", "pages": ["home", "services", "gallery", "about", "contact"],
               "sections": ["hero", "services_grid", "gallery_masonry", "pricing_table", "reviews", "whatsapp_float"],
               "trust": ["registered agency (if true)", "trips done", "24x7 support (if true)"], "cta": "whatsapp",
               "moods": ["bright", "calm", "blue"], "photos": ["destinations (real trips)", "vehicles", "happy groups (consented)"],
               "questions": ["Kaun si services: tours, taxi, tickets, visa?", "Popular packages (rate agar dikhana hai)?", "Office kahan?"],
               "legal": ["travel"], "styles": ["bold_modern", "organic_natural", "playful_bright"]},
    "hospitality": {"label": "Hotels, stays & venues", "goal": "booking", "pages": ["home", "gallery", "services", "booking", "contact"],
                    "sections": ["hero", "gallery_masonry", "features_split", "pricing_table", "map_hours", "booking_slots"],
                    "trust": ["ratings she gives", "location", "amenities"], "cta": "booking",
                    "moods": ["luxury", "calm", "earthy"], "photos": ["rooms", "views", "dining", "venue setups"],
                    "questions": ["Kitne rooms / hall capacity?", "Rates aur kya included?", "Check-in / booking kaise?"],
                    "legal": ["fssai"], "styles": ["luxury_dark", "organic_natural", "editorial_calm"]},
    "events": {"label": "Weddings & events", "goal": "portfolio", "pages": ["home", "portfolio", "services", "about", "contact"],
               "sections": ["hero", "portfolio_grid", "services_grid", "reviews", "process_steps", "cta_band"],
               "trust": ["events done (her number)", "team", "vendors"], "cta": "enquiry",
               "moods": ["festive", "luxury", "warm"], "photos": ["decor setups", "events (consented)", "team"],
               "questions": ["Kaun si service: decor, planning, DJ, photography...?", "Best events ki photos?", "Kaun se shehar?"],
               "legal": [], "styles": ["festive_traditional", "luxury_dark", "editorial_calm"]},
    "creative": {"label": "Creative & media", "goal": "portfolio", "pages": ["home", "portfolio", "services", "about", "contact"],
                 "sections": ["hero", "portfolio_grid", "services_grid", "process_steps", "reviews", "cta_band"],
                 "trust": ["clients (names with permission)", "years", "style"], "cta": "enquiry",
                 "moods": ["bold", "mono", "dark"], "photos": ["best work", "studio", "behind the scenes"],
                 "questions": ["Kaun sa kaam: photo, video, design, print, ads?", "Best 8-10 kaam?", "Packages (agar dikhane hain)?"],
                 "legal": [], "styles": ["minimal_swiss", "bold_modern", "luxury_dark"]},
    "it": {"label": "IT & software", "goal": "enquiry", "pages": ["home", "services", "portfolio", "about", "contact"],
           "sections": ["hero", "services_grid", "features_split", "portfolio_grid", "stats_counters", "cta_band"],
           "trust": ["projects / clients (real)", "tech stack", "support"], "cta": "enquiry",
           "moods": ["tech", "gradient", "blue"], "photos": ["team", "product screenshots", "office"],
           "questions": ["Kaun si services / product?", "Kaun se clients / projects dikhane hain?", "Demo / call kaise?"],
           "legal": [], "styles": ["tech_gradient", "minimal_swiss", "corporate_trust"]},
    "telecom": {"label": "Internet & telecom", "goal": "enquiry", "pages": ["home", "pricing", "coverage", "faq", "contact"],
                "sections": ["hero", "pricing_table", "coverage_areas", "features_split", "faq", "whatsapp_float"],
                "trust": ["licence / franchise (only real)", "local support team", "uptime"], "cta": "call",
                "moods": ["tech", "blue", "bold"], "photos": ["network / fibre work", "support team", "office"],
                "questions": ["Plans aur speed (rate agar dikhana hai)?", "Kaun se area / society?", "Installation charge aur time?"],
                "legal": [], "styles": ["tech_gradient", "bold_modern", "corporate_trust"]},
    "manufacturing": {"label": "Manufacturing & industry", "goal": "catalogue", "pages": ["home", "products", "about", "certificates", "contact"],
                      "sections": ["hero", "products_grid", "stats_counters", "certificates_trust", "process_steps", "contact_block"],
                      "trust": ["capacity (her figure)", "certifications (real)", "clients (with permission)"], "cta": "enquiry",
                      "moods": ["trust", "neutral", "contrast"], "photos": ["factory floor", "machines", "products"],
                      "questions": ["Kya banate ho?", "Capacity aur MOQ?", "Certifications / export?"],
                      "legal": ["legal_metrology"], "styles": ["corporate_trust", "minimal_swiss", "bold_modern"]},
    "agriculture": {"label": "Agriculture & farm", "goal": "catalogue", "pages": ["home", "products", "about", "contact"],
                    "sections": ["hero", "products_grid", "intro_story", "process_steps", "gallery_masonry", "whatsapp_float"],
                    "trust": ["farm / origin", "organic certificate (only real)", "direct from farmer"], "cta": "whatsapp",
                    "moods": ["green", "earthy"], "photos": ["fields", "harvest", "produce close-ups"],
                    "questions": ["Kya ugate / bechte ho?", "Kahan tak supply?", "Organic certificate hai?"],
                    "legal": ["fssai", "dmr"], "styles": ["organic_natural", "warm_local", "editorial_calm"]},
    "logistics": {"label": "Logistics & transport", "goal": "enquiry", "pages": ["home", "services", "coverage", "about", "contact"],
                  "sections": ["hero", "services_grid", "coverage_areas", "stats_counters", "process_steps", "cta_band"],
                  "trust": ["fleet (her number)", "routes", "insurance (if true)"], "cta": "call",
                  "moods": ["bold", "trust"], "photos": ["vehicles", "warehouse", "loading"],
                  "questions": ["Kaun si service: transport, courier, packers & movers?", "Routes / cities?", "Fleet size?"],
                  "legal": [], "styles": ["bold_modern", "corporate_trust", "tech_gradient"]},
    "trade": {"label": "Wholesale & trade", "goal": "catalogue", "pages": ["home", "products", "about", "contact"],
              "sections": ["hero", "products_grid", "stats_counters", "logos_marquee", "contact_block", "whatsapp_float"],
              "trust": ["years in trade", "brands handled (names, no logos without permission)", "dealer network"], "cta": "whatsapp",
              "moods": ["trust", "neutral", "bold"], "photos": ["godown", "stock", "dispatch"],
              "questions": ["Kaun se products / brands?", "Kaun se area supply?", "Dealer / bulk order kaise?"],
              "legal": ["legal_metrology"], "styles": ["corporate_trust", "bold_modern", "minimal_swiss"]},
    "ngo": {"label": "NGOs & community", "goal": "cause", "pages": ["home", "about", "projects", "donate", "contact"],
            "sections": ["hero", "donate_impact", "projects_case", "team", "certificates_trust", "cta_band"],
            "trust": ["registration", "12A / 80G (only real)", "reports"], "cta": "donate",
            "moods": ["warm", "green", "calm"], "photos": ["work on the ground", "volunteers", "beneficiaries (consented)"],
            "questions": ["Sanstha ka kaam aur registration?", "12A / 80G / FCRA hai?", "Daan kaise lete ho (UPI / bank)?"],
            "legal": ["ngo"], "styles": ["organic_natural", "warm_local", "editorial_calm"]},
    "spiritual": {"label": "Temples, spiritual & astrology", "goal": "info", "pages": ["home", "about", "events", "gallery", "contact"],
                  "sections": ["hero", "intro_story", "timeline_history", "gallery_masonry", "map_hours", "donate_impact"],
                  "trust": ["history", "trustees", "timings"], "cta": "contact",
                  "moods": ["festive", "warm"], "photos": ["the place", "festivals", "rituals (permitted)"],
                  "questions": ["Sthaan / seva ka naam aur history?", "Darshan / pooja timings?", "Daan / booking kaise?"],
                  "legal": ["astro", "ngo"], "styles": ["festive_traditional", "editorial_calm", "warm_local"]},
    "personal": {"label": "Personal brands & freelancers", "goal": "personal", "pages": ["home", "about", "services", "contact"],
                 "sections": ["hero", "intro_story", "services_grid", "portfolio_grid", "reviews", "contact_block"],
                 "trust": ["experience", "work samples", "clients (permitted)"], "cta": "enquiry",
                 "moods": ["mono", "bold", "calm"], "photos": ["portrait (real)", "at work", "work samples"],
                 "questions": ["Aap kya karte ho aur kiske liye?", "Best kaam / achievements?", "Contact ka tareeka?"],
                 "legal": [], "styles": ["editorial_calm", "minimal_swiss", "bold_modern"]},
    "pets": {"label": "Pets", "goal": "booking", "pages": ["home", "services", "products", "contact"],
             "sections": ["hero", "services_grid", "products_grid", "gallery_masonry", "reviews", "booking_slots"],
             "trust": ["trained staff", "vet registration (if vet)", "care"], "cta": "booking",
             "moods": ["bright", "candy", "warm"], "photos": ["happy pets (owners' consent)", "facility", "products"],
             "questions": ["Grooming, boarding, vet, pet shop?", "Rates?", "Timings / home service?"],
             "legal": ["vet"], "styles": ["playful_bright", "warm_local", "organic_natural"]},
    "kids": {"label": "Kids & childcare", "goal": "admissions", "pages": ["home", "about", "courses", "gallery", "contact"],
             "sections": ["hero", "intro_story", "courses_list", "gallery_masonry", "faq", "cta_band"],
             "trust": ["safety", "trained caregivers", "CCTV (if true)"], "cta": "enquiry",
             "moods": ["candy", "bright"], "photos": ["play area", "activities", "meals"],
             "questions": ["Daycare / play school / activity centre?", "Umar aur timings?", "Fees (agar dikhani hai)?"],
             "legal": ["edu"], "styles": ["playful_bright", "warm_local", "organic_natural"]},
    "staffing": {"label": "Staffing & security", "goal": "enquiry", "pages": ["home", "services", "about", "careers", "contact"],
                 "sections": ["hero", "services_grid", "stats_counters", "process_steps", "logos_marquee", "cta_band"],
                 "trust": ["licence (PSARA etc. if real)", "trained staff", "clients (permitted)"], "cta": "call",
                 "moods": ["trust", "bold"], "photos": ["staff in uniform", "training", "office"],
                 "questions": ["Kaun si staff service: security, housekeeping, placement?", "Licence / registration?", "Kaun se shehar?"],
                 "legal": ["hiring"], "styles": ["corporate_trust", "bold_modern", "minimal_swiss"]},
    "citizen_services": {"label": "Citizen & document services", "goal": "info", "pages": ["home", "services", "faq", "contact"],
                         "sections": ["hero", "services_grid", "process_steps", "faq", "map_hours", "whatsapp_float"],
                         "trust": ["years of service", "clear fees she charges", "privacy of documents"], "cta": "call",
                         "moods": ["trust", "calm"], "photos": ["service counter", "office"],
                         "questions": ["Kaun si services (PAN, passport help, bills, forms...)?", "Aapki service fees?", "Timings aur documents list?"],
                         "legal": ["govt_lookalike"], "styles": ["corporate_trust", "minimal_swiss", "warm_local"]},
    "crafts": {"label": "Crafts & artisans", "goal": "catalogue", "pages": ["home", "products", "about", "gallery", "contact"],
               "sections": ["hero", "products_grid", "intro_story", "process_steps", "gallery_masonry", "whatsapp_float"],
               "trust": ["handmade", "artisan story", "GI tag (only if real)"], "cta": "whatsapp",
               "moods": ["earthy", "festive", "warm"], "photos": ["making process", "products", "artisan"],
               "questions": ["Kya banate ho aur kaise?", "Order / shipping kaise?", "Custom order lete ho?"],
               "legal": ["legal_metrology"], "styles": ["editorial_calm", "organic_natural", "festive_traditional"]},
    "sports": {"label": "Sports", "goal": "booking", "pages": ["home", "services", "pricing", "gallery", "contact"],
               "sections": ["hero", "services_grid", "pricing_table", "team", "gallery_masonry", "booking_slots"],
               "trust": ["certified coaches", "facility", "achievements (real)"], "cta": "booking",
               "moods": ["bold", "contrast", "bright"], "photos": ["ground / turf", "training", "events"],
               "questions": ["Academy, turf booking ya sports shop?", "Slots / batches aur rates?", "Location?"],
               "legal": [], "styles": ["bold_modern", "playful_bright", "tech_gradient"]},
    "local_services": {"label": "Everyday local services", "goal": "enquiry", "pages": ["home", "services", "contact"],
                       "sections": ["hero", "services_grid", "pricing_table", "map_hours", "reviews", "whatsapp_float"],
                       "trust": ["years in the area", "quick service", "fair rates"], "cta": "whatsapp",
                       "moods": ["warm", "bright"], "photos": ["shop", "work", "owner"],
                       "questions": ["Kya service dete ho?", "Rate list?", "Pickup / delivery?"],
                       "legal": [], "styles": ["warm_local", "playful_bright", "minimal_swiss"]},
}


def check() -> list[str]:
    """Self-check of the fixed parts (used by tests and the library build)."""
    bad: list[str] = []
    if len(GOALS) != 10:
        bad.append("goals != 10")
    if len(STYLES) != 10:
        bad.append("styles != 10")
    if sum(len(v["variants"]) for v in SECTIONS.values()) != 300:
        bad.append("section designs != 300")
    if len(HEROES) != 24:
        bad.append("heroes != 24")
    if len(MOTION_PRESETS) != 60:
        bad.append("motion presets != 60")
    if len(PALETTES) != 50:
        bad.append(f"palettes != 50 ({len(PALETTES)})")
    if len(FONTS) != 30:
        bad.append("font pairs != 30")
    if len(INDUSTRIES) != 40:
        bad.append(f"industries != 40 ({len(INDUSTRIES)})")
    for k, st in STYLES.items():
        if st["fonts"] not in FONTS:
            bad.append(f"style {k}: font pair {st['fonts']}")
        for m in st["motion"]:
            if MOTION_ALIASES.get(m, m) not in MOTION_PRESETS:
                bad.append(f"style {k}: motion {m}")
        for h in st["heroes"]:
            if h not in HEROES:
                bad.append(f"style {k}: hero {h}")
    for k, ind in INDUSTRIES.items():
        for p in ind["pages"]:
            if p not in PAGES and p != "certificates":
                bad.append(f"{k}: page {p}")
        for sct in ind["sections"]:
            if sct not in SECTIONS:
                bad.append(f"{k}: section {sct}")
        for f in ind["legal"]:
            if f not in LEGAL:
                bad.append(f"{k}: legal {f}")
        for sty in ind["styles"]:
            if sty not in STYLES:
                bad.append(f"{k}: style {sty}")
    for g in GOALS.values():
        for sct in g["sections"]:
            if sct not in SECTIONS:
                bad.append(f"goal section {sct}")
        for p in g["pages"]:
            if p not in PAGES:
                bad.append(f"goal page {p}")
    return bad


# ---------------------------------------------------------------- v0.325 ANY DESIGN: free-form sections
# Besides the section library above, a page may carry FREE-FORM sections Opus designs from a name + brief ("EMI
# calculator", "Compare our 3 plans", "How an order travels"): type custom_<name>, at most CUSTOM_PER_PAGE a page.
CUSTOM = re.compile(r"custom_[a-z0-9_]{1,30}")
CUSTOM_PER_PAGE = 3


def custom_type(name: str) -> str:
    """'EMI calculator' -> 'custom_emi_calculator' (a stable key for the section file and its id)."""
    k = re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")[:30].strip("_")
    return f"custom_{k or 'block'}"


def is_section(t: Any) -> bool:
    return isinstance(t, str) and (t in SECTIONS or bool(CUSTOM.fullmatch(t)))


def label_of(s: Any) -> str:
    """A section's human label: its own (custom), the library's, or made from the key."""
    if isinstance(s, dict):
        t = str(s.get("type") or "")
        if s.get("label"):
            return str(s["label"])
    else:
        t = str(s or "")
    if t in SECTIONS:
        return SECTIONS[t]["label"]
    return t.replace("custom_", "").replace("_", " ").strip().capitalize() or "Section"
