"""The parts a complete ask has, per section. Data, not prose: the compiler, the score, the questions and the page all
read this one table. `required` slots are the ones worth a question; `options` are the tap answers."""
from __future__ import annotations

from typing import Any

ANATOMY_V = 3
SECTIONS: dict[str, dict[str, Any]] = {
    "web": {
        "label": "Web design", "makes": "a website or landing page", "engine": "Web Studio", "limit": 2000,
        "slots": [
            {"key": "what", "label": "What it is", "required": True, "q": "What is the business, in one line?",
             "eg": "Shree Balaji Sweets, a mithai shop in Akola"},
            {"key": "who", "label": "Who visits", "required": True, "q": "Who mainly visits this website?",
             "options": ["Local families", "Working professionals", "Business owners", "Students and parents", "Tourists"]},
            {"key": "action", "label": "The one key action", "required": True, "q": "What ONE thing should a visitor do?",
             "options": ["Message on WhatsApp", "Call us", "Book an appointment", "Buy online", "Send an enquiry"]},
            {"key": "pages", "label": "Pages", "required": False, "q": "Which pages should it have?",
             "eg": "Home, Services, Prices, Gallery, Contact"},
            {"key": "style", "label": "Look and feel", "required": False, "q": "How should it look?",
             "options": ["Warm and traditional", "Clean and modern", "Premium and minimal", "Bold and energetic", "Playful and bright"]},
            {"key": "content", "label": "Real content", "required": False, "q": "Any words, offers or details to show?"},
        ],
    },
    "app": {
        "label": "App", "makes": "a phone app for your business", "engine": "App Studio", "limit": 2000,
        "slots": [
            {"key": "what", "label": "What it is", "required": True, "q": "What is the app for, in one line?",
             "eg": "Sharma Kirana in Akola: order groceries for home delivery"},
            {"key": "users", "label": "Who uses it", "required": True, "q": "Who will use the app?",
             "options": ["My customers", "My staff", "Customers and staff", "Students and parents", "Patients"]},
            {"key": "job", "label": "The main job", "required": True, "q": "What is the ONE thing a user must be able to do on day 1?",
             "options": ["Place an order", "Book a slot", "See and pay a bill", "Track a delivery", "Mark attendance"]},
            {"key": "lists", "label": "What it keeps", "required": False, "q": "What does the app keep a list of?",
             "eg": "products with price and stock, orders, customers"},
            {"key": "money", "label": "Money", "required": False, "q": "How is money paid?",
             "options": ["UPI to my account", "Cash on delivery", "Credit (udhaar) book", "No payments in the app"]},
            {"key": "alerts", "label": "Updates", "required": False, "q": "What should users be told about?",
             "eg": "order accepted, out for delivery, delivered"},
            {"key": "platform", "label": "Phones", "required": False, "q": "Which phones?",
             "options": ["Android", "iPhone", "Android and iPhone"]},
            {"key": "language", "label": "App language", "required": False, "q": "Which language should the app show?",
             "options": ["English", "Hindi", "Marathi", "English and Hindi"]},
        ],
    },
    "image": {
        "label": "Image and poster", "makes": "a picture, poster, banner or logo", "engine": "Create - Image", "limit": 1800,
        "slots": [
            {"key": "subject", "label": "Main subject", "required": True, "q": "What is the main thing in the picture?",
             "eg": "a brass diya with marigold flowers"},
            {"key": "scene", "label": "Where / what is happening", "required": False, "q": "Where is it, or what is happening?"},
            {"key": "style", "label": "Kind of picture", "required": True, "q": "What kind of picture is it?",
             "options": ["Real photograph", "Festive poster", "Flat illustration", "Simple logo", "Product photo"]},
            {"key": "words", "label": "Exact words on it", "required": False, "q": "Should any words be written on it? Type them exactly."},
            {"key": "size", "label": "Shape", "required": True, "q": "Where will you use it?",
             "options": ["1:1", "4:5", "9:16", "16:9"],
             "option_labels": ["Square post", "Tall post / poster", "Story or reel", "Wide banner"]},
            {"key": "colours", "label": "Colours", "required": False, "q": "Which colours?"},
            {"key": "composition", "label": "Layout", "required": False, "q": "Where should things sit in the frame?"},
            {"key": "light", "label": "Light", "required": False, "q": "What kind of light?"},
        ],
    },
    "script": {
        "label": "Script", "makes": "a script for a reel, ad or video", "engine": "Create - Script writer", "limit": 2500,
        "slots": [
            {"key": "platform", "label": "Where it will play", "required": True, "q": "Where will this video play?",
             "options": ["Instagram reel", "YouTube Short", "YouTube video", "WhatsApp status video", "TV / cable ad"]},
            {"key": "length", "label": "Length", "required": True, "q": "How long should it be?",
             "options": ["15 seconds", "30 seconds", "45 seconds", "60 seconds"]},
            {"key": "audience", "label": "Who it is for", "required": True, "q": "Who should stop scrolling for this?"},
            {"key": "message", "label": "The one message", "required": True, "q": "What ONE thing should they remember?"},
            {"key": "hook", "label": "Opening hook", "required": False, "q": "How should the first 3 seconds open?"},
            {"key": "cta", "label": "Last line (what to do)", "required": True, "q": "What should they do at the end?",
             "options": ["Message on WhatsApp", "Visit the shop", "Call now", "Order online", "Follow the page"]},
            {"key": "tone", "label": "Tone", "required": False, "q": "What should it feel like?",
             "options": ["Warm", "Funny", "Emotional", "Energetic", "Straight and honest"]},
            {"key": "language", "label": "Spoken language", "required": False, "q": "Which language should they speak?",
             "options": ["Hinglish", "Hindi", "English", "Marathi"]},
        ],
    },
    "video": {
        "label": "Video clip", "makes": "a short video clip made by AI", "engine": "Create - Video", "limit": 1500,
        "slots": [
            {"key": "subject", "label": "Who or what is in it", "required": True, "q": "Who or what is in the shot?",
             "eg": "a steaming cup of masala chai on a wooden table"},
            {"key": "action", "label": "The one thing that happens", "required": True, "q": "What ONE thing happens in the clip?",
             "eg": "milk is poured in and the colour turns golden"},
            {"key": "camera", "label": "Camera move", "required": False, "q": "How should the camera move?",
             "options": ["Still camera", "Slow push in", "Slow pan left to right", "Orbit around", "Top-down"]},
            {"key": "place", "label": "Where", "required": False, "q": "Where is it happening?"},
            {"key": "light", "label": "Light", "required": False, "q": "What kind of light?",
             "options": ["Soft morning light", "Warm evening glow", "Bright daylight", "Festive lamps at night"]},
            {"key": "style", "label": "Look", "required": False, "q": "What should it look like?",
             "options": ["Real film", "Product advert", "Animated", "Slow-motion close-up"]},
            {"key": "size", "label": "Shape", "required": True, "q": "Where will you use it?",
             "options": ["9:16", "16:9", "1:1"], "option_labels": ["Reel or story", "YouTube / wide", "Square post"]},
            {"key": "length", "label": "Length", "required": False, "q": "How long?",
             "options": ["5 seconds", "8 seconds", "10 seconds"]},
        ],
    },
    "music": {
        "label": "Music and jingle", "makes": "a song, jingle or background music", "engine": "Create - Music", "limit": 1500,
        "slots": [
            {"key": "use", "label": "What it is for", "required": True, "q": "What is the music for?",
             "options": ["Shop jingle", "Reel background", "Festival song", "Ad music", "Event / wedding"]},
            {"key": "genre", "label": "Kind of music", "required": True, "q": "What kind of music?",
             "options": ["Bollywood pop", "Folk", "Devotional", "Lo-fi", "Indie acoustic", "EDM"]},
            {"key": "mood", "label": "Mood", "required": True, "q": "How should it feel?",
             "options": ["Happy", "Festive", "Calm", "Romantic", "Energetic", "Emotional"]},
            {"key": "vocals", "label": "Voice", "required": False, "q": "Who sings, if anyone?",
             "options": ["Instrumental, no singing", "Female voice", "Male voice", "Duet", "Children's chorus"]},
            {"key": "language", "label": "Song language", "required": False, "q": "Which language are the words in?",
             "options": ["Hindi", "Hinglish", "Marathi", "Punjabi", "English"]},
            {"key": "instruments", "label": "Instruments", "required": False, "q": "Any instruments to hear?",
             "eg": "dholak, flute, acoustic guitar"},
            {"key": "tempo", "label": "Speed", "required": False, "q": "How fast?",
             "options": ["Slow", "Medium", "Fast"]},
            {"key": "lyrics", "label": "Lyrics or a line to sing", "required": False, "q": "Any words to sing? Type them exactly."},
            {"key": "length", "label": "Length", "required": False, "q": "How long?",
             "options": ["15 seconds", "30 seconds", "60 seconds", "2 minutes"]},
        ],
    },
    "marketing": {
        "label": "Marketing message", "makes": "a WhatsApp, email, SMS or social message", "engine": "Hoola chat (drafts only)",
        "limit": 1800,
        "slots": [
            {"key": "channel", "label": "Where it goes", "required": True, "q": "Where will this message go?",
             "options": ["WhatsApp message", "Email", "SMS", "Instagram caption", "Facebook / Google ad"]},
            {"key": "audience", "label": "Who gets it", "required": True, "q": "Who is this message for?",
             "options": ["My regular customers", "New customers", "Customers who have not come back", "Students and parents"]},
            {"key": "offer", "label": "The offer or news", "required": True, "q": "What is the offer or news, exactly?",
             "eg": "Flat 20% off on all sarees till 15 Nov"},
            {"key": "action", "label": "What they should do", "required": True, "q": "What should they do after reading?",
             "options": ["Reply on WhatsApp", "Visit the shop", "Call now", "Book online", "Order online"]},
            {"key": "tone", "label": "Tone", "required": False, "q": "How should it sound?",
             "options": ["Warm and friendly", "Short and direct", "Festive", "Respectful and formal"]},
            {"key": "language", "label": "Language", "required": False, "q": "Which language?",
             "options": ["Hinglish", "Hindi", "English", "Marathi"]},
            {"key": "sender", "label": "Signed as", "required": False, "q": "Who is it from?", "eg": "Team Shree Balaji Sweets"},
        ],
    },
    "doc": {
        "label": "Business document", "makes": "a proposal, quotation, letter, report or policy", "engine": "Hoola chat - documents",
        "limit": 2500,
        "slots": [
            {"key": "kind", "label": "Kind of document", "required": True, "q": "What kind of document is it?",
             "options": ["Proposal", "Quotation", "Letter", "Report", "Policy", "Notice"]},
            {"key": "reader", "label": "Who reads it", "required": True, "q": "Who will read it?",
             "eg": "the purchase head of ABC Industries"},
            {"key": "purpose", "label": "What it must achieve", "required": True, "q": "What should the reader do or decide after reading?",
             "eg": "approve the annual maintenance contract"},
            {"key": "content", "label": "Facts and numbers", "required": False, "q": "Which facts, items and numbers must be in it?"},
            {"key": "parts", "label": "Parts", "required": False, "q": "Which parts should it have?",
             "eg": "scope, timeline, price table, terms"},
            {"key": "tone", "label": "Tone", "required": False, "q": "How should it sound?",
             "options": ["Formal", "Friendly and professional", "Firm", "Simple and plain"]},
            {"key": "length", "label": "Length", "required": False, "q": "How long?",
             "options": ["One page", "Two to three pages", "As long as needed"]},
            {"key": "format", "label": "File", "required": True, "q": "Which file do you want?",
             "options": ["PDF", "Word document", "Text in the chat"]},
            {"key": "sender", "label": "From", "required": False, "q": "Who is it from?", "eg": "Meghana, Newtika Pvt Ltd"},
        ],
    },
    "code": {
        "label": "Coding", "makes": "a coding job for Hoola Code", "engine": "Hoola Code", "limit": 4000,
        "slots": [
            {"key": "kind", "label": "Kind of job", "required": True, "q": "What kind of coding job is it?",
             "options": ["Fix a bug", "New feature", "Add tests", "Change how something looks", "Explain the code", "Docs"]},
            {"key": "task", "label": "What is wrong / what to build", "required": True,
             "q": "What exactly is wrong, or what should be built? Paste the error if there is one.",
             "eg": "the checkout page shows Rs 0 when a coupon is applied"},
            {"key": "where", "label": "Where in the code", "required": False, "q": "Which file, page or screen is it in?",
             "eg": "server/app/shop.py, the cart total"},
            {"key": "done", "label": "Done means", "required": True, "q": "How will you know it is fixed or finished?",
             "eg": "the total after a 10% coupon on Rs 500 shows Rs 450"},
            {"key": "check", "label": "The check to run", "required": False, "q": "Which check should prove it?",
             "options": ["Run the tests", "The build passes", "Add a test that fails first", "I will check by hand"]},
            {"key": "rules", "label": "Rules to follow", "required": False, "q": "Any rules to follow?",
             "eg": "keep the old API working, no new libraries"},
            {"key": "avoid", "label": "Do not touch", "required": False, "q": "Anything it must not change?", "eg": "the payment code"},
        ],
    },
    "research": {
        "label": "Research", "makes": "a research question with sources", "engine": "Hoola research", "limit": 2500,
        "slots": [
            {"key": "question", "label": "The question", "required": True, "q": "What exactly do you want to find out?",
             "eg": "the cheapest way to ship 5 kg parcels from Akola to Pune"},
            {"key": "decision", "label": "What you will decide", "required": True, "q": "What will you decide with the answer?",
             "eg": "which courier to sign up with"},
            {"key": "parts", "label": "Sub-questions", "required": False, "q": "Which smaller questions should it answer?",
             "eg": "price per kg, delivery days, pickup from my shop"},
            {"key": "sources", "label": "Sources to trust", "required": False, "q": "Which sources should it trust?",
             "options": ["Official / government sites first", "Company websites", "Any reliable source", "Research papers"]},
            {"key": "region", "label": "Where", "required": False, "q": "For which place?", "eg": "Maharashtra"},
            {"key": "asof", "label": "As of", "required": False, "q": "How recent must it be?",
             "options": ["The latest", "This year", "Last 12 months"]},
            {"key": "form", "label": "Form of the answer", "required": True, "q": "How should the answer look?",
             "options": ["A short answer", "A comparison table", "A report with sources", "A PDF report"]},
        ],
    },
    "data": {
        "label": "Data and sheets", "makes": "a question about your numbers, a sheet or a chart", "engine": "Hoola chat - Python",
        "limit": 2500,
        "slots": [
            {"key": "data", "label": "The data", "required": True, "q": "Which data? Name the file or sheet, or paste it.",
             "eg": "sales_october.xlsx, the Orders sheet"},
            {"key": "question", "label": "The question", "required": True, "q": "What do you want to know from it?",
             "eg": "which 5 products made the most profit"},
            {"key": "output", "label": "The result", "required": True, "q": "What should come out?",
             "options": ["A table", "A chart", "A formula for my sheet", "A short summary", "An Excel file"]},
            {"key": "period", "label": "Period", "required": False, "q": "For which dates?", "eg": "1 to 31 October"},
            {"key": "checks", "label": "Checks", "required": False, "q": "Any number it must match?",
             "eg": "the total must equal the Rs 4,82,000 in my books"},
        ],
    },
    "aiapp": {
        "label": "AI assistant", "makes": "an AI that answers your customers", "engine": "Hoola AI Apps", "limit": 3000,
        "slots": [
            {"key": "role", "label": "Its job", "required": True, "q": "What is the AI's job?",
             "options": ["Answer questions", "Take bookings", "Take orders", "Collect enquiries", "Support after a sale"]},
            {"key": "business", "label": "Your business", "required": True, "q": "Which business, in one line?",
             "eg": "Roop Salon in Pune, women's hair and skin"},
            {"key": "knows", "label": "What it knows", "required": True, "q": "Which facts may it answer from? Timings, prices, policies…",
             "eg": "open 10 am to 8 pm, closed Tuesday, haircut Rs 300"},
            {"key": "never", "label": "What it must never say", "required": True, "q": "What must it never say or promise?",
             "eg": "never promise a discount, never give medical advice"},
            {"key": "handoff", "label": "When it calls you", "required": False, "q": "When should it hand over to you?",
             "options": ["A complaint", "A question it cannot answer", "A booking change", "Anyone who asks for a person"]},
            {"key": "tone", "label": "Tone", "required": False, "q": "How should it sound?",
             "options": ["Warm and friendly", "Short and polite", "Formal"]},
            {"key": "language", "label": "Language", "required": False, "q": "Which language?",
             "options": ["The customer's own language", "Hinglish", "Hindi", "English", "Marathi"]},
            {"key": "channel", "label": "Where it answers", "required": False, "q": "Where will customers talk to it?",
             "options": ["My website", "My WhatsApp number", "A link I share"]},
        ],
    },
    "chat": {
        "label": "Everyday ask", "makes": "any other question or job for Hoola", "engine": "Hoola chat", "limit": 2500,
        "slots": [
            {"key": "goal", "label": "What you want", "required": True, "q": "What do you want, in one line?",
             "eg": "a polite reply to a customer who says the cake was late"},
            {"key": "context", "label": "Background", "required": False, "q": "What should Hoola know first?",
             "eg": "she is a regular, the delivery was 40 minutes late"},
            {"key": "form", "label": "Form of the answer", "required": True, "q": "How should the answer look?",
             "options": ["A short answer", "Steps", "A table", "A message I can send", "A list of ideas"]},
            {"key": "example", "label": "An example", "required": False, "q": "Any example of what you like?"},
            {"key": "avoid", "label": "Avoid", "required": False, "q": "Anything to avoid?"},
        ],
    },
}
# the first three sections keep their place (P1); P5's and P6's five each follow in the plan's order
SECTIONS = {k: SECTIONS[k] for k in ("web", "image", "script", "app", "video", "music", "marketing", "doc",
                                  "code", "research", "data", "aiapp", "chat")}
ORDER = tuple(SECTIONS)


def slots(section: str) -> list[dict[str, Any]]:
    return SECTIONS[section]["slots"]


def slot(section: str, key: str) -> dict[str, Any] | None:
    return next((s for s in slots(section) if s["key"] == key), None)


def keys(section: str) -> list[str]:
    return [s["key"] for s in slots(section)]


def required(section: str) -> list[str]:
    return [s["key"] for s in slots(section) if s.get("required")]


def public() -> list[dict[str, Any]]:
    """The table as the page needs it."""
    return [{"key": k, "label": v["label"], "makes": v["makes"], "engine": v["engine"],
             "slots": [{x: s[x] for x in ("key", "label", "required", "q", "options", "option_labels", "eg") if x in s}
                       for s in v["slots"]]} for k, v in SECTIONS.items()]
