"""The parts a complete ask has, per section. Data, not prose: the compiler, the score, the questions and the page all
read this one table. `required` slots are the ones worth a question; `options` are the tap answers."""
from __future__ import annotations

from typing import Any

ANATOMY_V = 1
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
}
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
