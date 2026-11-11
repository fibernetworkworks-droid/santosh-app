"""HOOLA DESIGN D8b: the template gallery (docs/HOOLA_DESIGN_PLAN.md section 8, D8b).

BUILT-IN TEMPLATES are written in code, in the same spec words the design AI writes (ai.py GRAMMAR: frames with auto
layout, text, shapes, icons, picture placeholders). They go through exactly the AI's path - ai.clean_spec (only known
keys, fonts from the editor's list), ai.build (contract nodes, the server's layout pass, the contrast check of every
text) - so each one is a valid Hoola Design document by construction. Original work: shapes, gradients, text and the
editor's own icons; no image, logo or font file of anyone else. Facts only she knows are marked [blanks] ([phone
number], ₹[price], [date] ...): a template never invents a phone number, a price or an address.

"Use template" = a NEW file in her files holding that document (ids minted under client number 1, so the file's
next client number starts at 2 and no editor ever mints one of them again). Each frame carries the AI's `aiSettle`
mark: the first editor that opens the file lays the text out once with the real fonts.

HER OWN TEMPLATES ("My templates"): POST /files/{id}/publish-template keeps a copy of HER file as a template - only by
her explicit action, only for herself (stored under her own tenant folder, never listed to anybody else, never
public), `reviewed: false`. Using one makes a new file exactly like "Duplicate" (the ids and the client counter are
carried over).

Thumbnails: built-in ones are drawn here as a small SVG from the laid-out nodes (rects, ellipses, gradients, icons,
wrapped text - an estimate of the editor's real drawing; fonts fall back to the system's); her own templates keep
the PNG thumbnail her editor last saved, else the same SVG drawing.
"""
from __future__ import annotations

import json
import math
import re
import secrets
import threading
import time
from html import escape as _esc
from pathlib import Path
from typing import Any

from . import ai, ailayout
from .doc import FIRST_PAGE, ROOT, dumps_nodes, loads, new_document

MINE_MAX = 50                       # her own templates kept per account
MINE_NODES = 50_000                 # a file larger than this is not kept as a template
MINE_BYTES = 12 * 1024 * 1024
THUMB_W = 480

CATEGORIES = ("Posters", "Festivals", "Social media", "Business", "Invitations", "Food", "App screens",
              "Presentations", "YouTube", "Certificates", "Websites")


# =============================================================================================== spec words
def T(chars: str, size: float, weight: int = 400, color: str = "#111827", **kw: Any) -> dict:
    return {"type": "text", "chars": chars, "size": size, "weight": weight, "color": color, **kw}


def F(name: str, layout: str, children: list, **kw: Any) -> dict:
    return {"type": "frame", "name": name, "layout": layout, "children": [c for c in children if c], **kw}


def I(icon: str, size: float, color: str, **kw: Any) -> dict:
    return {"type": "icon", "icon": icon, "size": size, "color": color, **kw}


def IMG(label: str, **kw: Any) -> dict:
    return {"type": "image", "label": label, **kw}


def E(x: float, y: float, w: float, h: float, fill: Any, **kw: Any) -> dict:
    return {"type": "ellipse", "x": x, "y": y, "w": w, "h": h, "fill": fill, **kw}


def R(x: float, y: float, w: float, h: float, fill: Any, **kw: Any) -> dict:
    return {"type": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, **kw}


def pill(text: str, fill: Any, ink: str, size: float, pad: list | None = None, icon: str = "", font: str = "", **kw: Any) -> dict:
    t = T(text, size, 600, ink, **({"font": font} if font else {}))
    return F("Pill", "row", [I(icon, round(size * 1.15), ink) if icon else None, t], gap=_g(size * 0.5), align="center",
             justify="center", pad=pad or [round(size * 0.55), round(size * 1.1), round(size * 0.55), round(size * 1.1)],
             radius=999, fill=fill, w="hug", **kw)


def _g(v: float) -> int:
    return max(4, int(round(v / 4.0) * 4))


def stage(name: str, w: int, h: int, fill: Any, decor: list, content: dict) -> dict:
    """A free top frame: decoration first (drawn behind), then ONE content frame over the whole size."""
    content = {**content, "x": 0, "y": 0, "w": w, "h": h}
    return F(name, "none", decor + [content], w=w, h=h, fill=fill)


def info_row(icon: str, text: str, ink: str, size: float, icon_ink: str = "", font: str = "") -> dict:
    return F("Info", "row", [I(icon, round(size * 1.2), icon_ink or ink),
                             T(text, size, 500, ink, **({"font": font} if font else {}))], gap=_g(size * 0.6), align="center", w="hug")


# =============================================================================================== the templates
def _sale_poster() -> dict:
    ink, gold = "#FFFFFF", "#FBBF24"
    return stage("Sale poster", 1240, 1754, {"from": "#1E1B4B", "to": "#3B0764", "angle": 160}, [
        E(640, -260, 900, 900, "#7C3AED", opacity=0.35), E(-300, 1180, 820, 820, "#4F46E5", opacity=0.3),
        E(860, 560, 300, 300, gold, opacity=0.12)],
        F("Content", "column", [
            F("Top", "column", [
                pill("SEASON SALE", gold, "#1E1B4B", 32, icon="tag"),
                T("Big sale\nis here", 168, 700, ink, font="Sora", lineHeight=1.0, letterSpacing=-4),
                T("Up to [X]% off on [your best products]. Only for a few days.", 48, 400, "#E0E7FF", lineHeight=1.35, w=900),
            ], gap=48),
            F("Details", "column", [
                F("Offer", "row", [
                    F("Badge", "column", [T("UP TO", 32, 600, "#1E1B4B", letterSpacing=4),
                                          T("[X]%", 104, 700, "#1E1B4B", font="Sora", lineHeight=1.0),
                                          T("OFF", 32, 600, "#1E1B4B", letterSpacing=4)],
                      gap=4, align="center", justify="center", w=320, h=320, radius=999, fill=gold),
                    F("Lines", "column", [info_row("calendar", "[Sale dates]", ink, 40, gold),
                                          info_row("map-pin", "[your address]", ink, 40, gold),
                                          info_row("phone", "[phone number]", ink, 40, gold)], gap=32, w="fill"),
                ], gap=64, align="center"),
                F("Footer", "row", [T("[Your shop name]", 44, 700, ink, font="Sora"),
                                    pill("Visit us today", "#FFFFFF", "#3B0764", 32, icon="arrow-right")],
                  justify="between", align="center", pad=[40, 0, 0, 0]),
            ], gap=64),
        ], pad=120, justify="between"))


def _diwali_poster() -> dict:
    gold, cream = "#FBBF24", "#FFF7E6"
    return stage("Diwali poster", 1240, 1754, {"from": "#4A0D2B", "to": "#1F0614", "angle": 180}, [
        E(170, 280, 900, 900, "#F59E0B", opacity=0.10), E(370, 480, 500, 500, "#FBBF24", opacity=0.12),
        E(-120, 1400, 360, 360, "#F59E0B", opacity=0.16), E(1000, 1420, 360, 360, "#F59E0B", opacity=0.16)],
        F("Content", "column", [
            F("Top", "column", [I("sparkle", 72, gold, filled=True),
                                T("शुभ दीपावली", 168, 400, gold, font="Yatra One", align="center", lineHeight=1.15),
                                T("Happy Diwali", 64, 600, cream, font="Poppins", align="center", letterSpacing=2),
                                T("May the festival of lights fill your home with joy, health and success.", 40, 400, "#F5D9C8",
                                  font="Poppins", align="center", lineHeight=1.45, w=860)], gap=40, align="center"),
            F("Offer", "column", [T("दीपावली ऑफ़र", 40, 600, "#4A0D2B", font="Poppins", align="center"),
                                  T("Festive offers on [your products] till [last date]", 44, 700, "#4A0D2B", font="Poppins",
                                    align="center", lineHeight=1.3, w="fill")],
              gap=12, align="center", pad=[48, 64, 48, 64], radius=32, fill=gold, w=900),
            F("Footer", "column", [T("[Your shop name]", 48, 700, cream, font="Poppins", align="center"),
                                   F("Contact", "row", [info_row("phone", "[phone number]", "#F5D9C8", 32, gold, "Poppins"),
                                                        info_row("map-pin", "[your address]", "#F5D9C8", 32, gold, "Poppins")],
                                     gap=48, align="center", w="hug")], gap=20, align="center"),
        ], pad=[140, 120, 120, 120], justify="between", align="center"))


def _eid_poster() -> dict:
    gold, mint = "#E9C46A", "#D1FAE5"
    return stage("Eid poster", 1240, 1754, {"from": "#064E3B", "to": "#022C22", "angle": 180}, [
        E(780, 140, 300, 300, gold), E(850, 100, 300, 300, "#064E3B"),
        E(-260, 1260, 760, 760, "#10B981", opacity=0.10), E(820, 1340, 600, 600, "#10B981", opacity=0.08)],
        F("Content", "column", [
            F("Top", "column", [T("عید مبارک", 96, 400, gold, font="Noto Nastaliq Urdu"),
                                T("Eid Mubarak", 160, 700, "#FFFFFF", font="Playfair Display", lineHeight=1.05),
                                T("Wishing you and your family peace, happiness and many blessings.", 44, 400, mint,
                                  font="Playfair Display", lineHeight=1.45, w=900)], gap=40),
            F("Footer", "column", [R(0, 0, 160, 4, gold, name="Rule"),
                                   T("With warm wishes from", 36, 400, mint, font="Playfair Display"),
                                   T("[Your business name]", 56, 700, "#FFFFFF", font="Playfair Display")], gap=20),
        ], pad=[360, 120, 140, 120], justify="between"))


def _christmas_poster() -> dict:
    gold, snow = "#FCD34D", "#FFFFFF"
    dots = [E(x, y, s, s, snow, opacity=0.5) for x, y, s in
            ((120, 180, 16), (340, 90, 10), (520, 220, 14), (900, 140, 18), (1080, 300, 12), (200, 520, 10), (1010, 640, 16),
             (80, 900, 14), (1140, 980, 10), (300, 1240, 12), (960, 1300, 14), (620, 60, 12))]
    return stage("Christmas poster", 1240, 1754, {"from": "#0B1B3A", "to": "#14365E", "angle": 180}, dots + [
        E(-200, 1380, 1640, 700, "#FFFFFF", opacity=0.9)],
        F("Content", "column", [
            F("Top", "column", [I("star", 120, gold, filled=True),
                                T("Merry\nChristmas", 176, 400, snow, font="DM Serif Display", align="center", lineHeight=1.0),
                                T("and a happy new year", 56, 500, gold, font="Montserrat", align="center", letterSpacing=1)],
              gap=48, align="center"),
            F("Footer", "column", [T("Christmas offers at [Your shop name]", 48, 700, "#0B1B3A", font="Montserrat", align="center"),
                                   T("[Offer dates] · [your address]", 36, 500, "#334155", font="Montserrat", align="center")],
              gap=16, align="center"),
        ], pad=[200, 120, 120, 120], justify="between", align="center"))


def _coaching_poster() -> dict:
    accent, ink, sub = "#4338CA", "#0F172A", "#475569"
    feat = lambda icon, title, line: F("Feature", "column", [                                             # noqa: E731
        F("Icon", "row", [I(icon, 48, accent)], pad=20, radius=24, fill="#EEF2FF", w="hug"),
        T(title, 40, 700, ink, font="Plus Jakarta Sans"), T(line, 30, 400, sub, font="Plus Jakarta Sans", lineHeight=1.4)],
        gap=16, pad=40, radius=32, fill="#FFFFFF", stroke={"color": "#E2E8F0", "width": 2}, w="fill")
    return stage("Coaching poster", 1240, 1754, "#F8FAFC", [
        R(0, 0, 1240, 760, {"from": "#4338CA", "to": "#312E81", "angle": 135}), E(820, -200, 600, 600, "#6366F1", opacity=0.5)],
        F("Content", "column", [
            F("Hero", "column", [pill("ADMISSIONS OPEN", "#FACC15", "#1E1B4B", 30),
                                 T("Learn better.\nScore higher.", 120, 700, "#FFFFFF", font="Plus Jakarta Sans", lineHeight=1.05, letterSpacing=-2),
                                 T("[Subjects] coaching for [classes / exam] · [Board]", 40, 500, "#E0E7FF", font="Plus Jakarta Sans")], gap=40),
            F("Features", "column", [
                F("Row 1", "row", [feat("user", "Expert teachers", "[Years] of teaching experience"),
                                   feat("check", "Small batches", "Personal attention for every student")], gap=32),
                F("Row 2", "row", [feat("calendar", "Weekly tests", "Track progress every week"),
                                   feat("chat", "Doubt sessions", "Ask anything, any day")], gap=32)], gap=32),
            F("Contact", "row", [F("Text", "column", [T("New batch starts [date]", 44, 700, "#FFFFFF", font="Plus Jakarta Sans"),
                                                      T("[your address]", 30, 400, "#E0E7FF", font="Plus Jakarta Sans")], gap=8, w="fill"),
                                 pill("[phone number]", "#FFFFFF", accent, 32, icon="phone")],
              gap=32, align="center", pad=[48, 56, 48, 56], radius=32, fill=accent),
        ], pad=[120, 96, 96, 96], gap=72))


def _grand_opening() -> dict:
    ink = "#3B0A1F"
    return stage("Grand opening post", 1080, 1080, {"from": "#FFE4E6", "to": "#FED7AA", "angle": 135}, [
        E(640, -180, 620, 620, "#FB7185", opacity=0.25), E(-200, 700, 560, 560, "#F97316", opacity=0.18)],
        F("Content", "column", [
            T("GRAND OPENING", 32, 600, "#9F1239", font="Outfit", letterSpacing=8),
            T("We are opening\nour doors", 112, 700, ink, font="Outfit", lineHeight=1.05, letterSpacing=-2),
            T("Come and celebrate with us at [Your shop name].", 40, 400, "#6B2737", font="Outfit", lineHeight=1.4, w=800),
            F("Details", "row", [info_row("calendar", "[Date]", ink, 32, "#E11D48", "Outfit"),
                                 info_row("clock", "[Time]", ink, 32, "#E11D48", "Outfit")], gap=48, w="hug"),
            info_row("map-pin", "[your address]", ink, 32, "#E11D48", "Outfit"),
            pill("See you there", "#9F1239", "#FFFFFF", 32, icon="arrow-right", font="Outfit"),
        ], pad=96, gap=32, justify="end"))


def _new_arrival() -> dict:
    return F("New arrival post", "column", [
        IMG("Your product photo", h="fill", fill="#E7E5E4"),
        F("Band", "row", [
            F("Text", "column", [T("NEW ARRIVAL", 28, 600, "#A16207", font="Manrope", letterSpacing=6),
                                 T("[Product name]", 72, 700, "#1C1917", font="Manrope", lineHeight=1.1),
                                 T("[One line about what makes it special]", 32, 400, "#57534E", font="Manrope")], gap=12, w="fill"),
            F("Price", "column", [T("₹[price]", 48, 700, "#FFFFFF", font="Manrope")], pad=[28, 40, 28, 40], radius=24, fill="#1C1917", w="hug"),
        ], gap=32, align="center", pad=[56, 72, 64, 72], fill="#FAFAF9"),
    ], w=1080, h=1080, fill="#FAFAF9")


def _story_offer() -> dict:
    return stage("Offer story", 1080, 1920, {"from": "#6D28D9", "to": "#BE185D", "angle": 160}, [
        E(560, -240, 760, 760, "#FFFFFF", opacity=0.10), E(-260, 1300, 820, 820, "#FFFFFF", opacity=0.08)],
        F("Content", "column", [
            pill("TODAY ONLY", "#FFFFFF", "#7C3AED", 32, icon="bolt"),
            F("Middle", "column", [T("[Your offer]", 144, 700, "#FFFFFF", font="Sora", lineHeight=1.0, letterSpacing=-3),
                                   T("on everything at [Your shop name]", 48, 400, "#FCE7F3", font="Sora", lineHeight=1.35)], gap=32),
            F("Bottom", "column", [F("Card", "column", [T("Use code", 32, 500, "#6B21A8", font="Sora"),
                                                        T("[CODE]", 72, 700, "#3B0764", font="Sora", letterSpacing=6)],
                                     gap=8, align="center", pad=48, radius=32, fill="#FFFFFF"),
                                   T("Tap the link in our bio to shop", 36, 500, "#FFFFFF", font="Sora", align="center", w="fill")], gap=40),
        ], pad=[200, 96, 160, 96], justify="between"))


def _whatsapp_status() -> dict:
    green, ink = "#047857", "#0B1F17"
    return F("WhatsApp status", "column", [
        F("Top", "column", [T("Good morning!", 44, 600, "#065F46", font="Poppins"),
                            T("Today's special", 120, 700, ink, font="Poppins", lineHeight=1.05, letterSpacing=-2)], gap=8),
        IMG("Photo of today's special", h=880, radius=48, fill="#D1FAE5"),
        F("Item", "row", [F("Name", "column", [T("[Item name]", 56, 700, ink, font="Poppins"),
                                               T("[Short detail]", 32, 400, "#3F5B50", font="Poppins")], gap=8, w="fill"),
                          T("₹[price]", 64, 700, green, font="Poppins")], align="center", gap=24),
        F("Order", "row", [I("chat", 40, "#FFFFFF"), T("Order on WhatsApp: [phone number]", 36, 600, "#FFFFFF", font="Poppins")],
          gap=16, align="center", justify="center", pad=[36, 40, 36, 40], radius=999, fill=green),
    ], w=1080, h=1920, pad=[160, 80, 140, 80], gap=48, justify="between", fill={"from": "#ECFDF5", "to": "#FFFFFF", "angle": 180})


def _business_card() -> dict:
    accent = "#0F766E"
    return F("Business card", "row", [
        F("Brand", "column", [F("Mark", "row", [T("[A]", 72, 700, accent, font="Sora")], justify="center", align="center",
                                w=160, h=160, radius=999, fill="#FFFFFF"),
                              T("[Your business name]", 28, 600, "#FFFFFF", font="Sora", align="center", w="fill")],
          gap=24, align="center", justify="center", pad=48, w=380, h="fill", fill={"from": "#0F766E", "to": "#134E4A", "angle": 160}),
        F("Details", "column", [
            F("Name", "column", [T("[Your name]", 52, 700, "#0F172A", font="Sora"), T("[Your role]", 26, 500, accent, font="Inter")], gap=8),
            {"type": "line", "color": "#E2E8F0", "width": 2},
            F("Lines", "column", [info_row("phone", "[phone number]", "#334155", 24, accent, "Inter"),
                                  info_row("mail", "[email]", "#334155", 24, accent, "Inter"),
                                  info_row("globe", "[website]", "#334155", 24, accent, "Inter"),
                                  info_row("map-pin", "[your address]", "#334155", 24, accent, "Inter")], gap=16),
        ], gap=32, pad=[64, 64, 64, 64], w="fill", h="fill", justify="center"),
    ], w=1050, h=600, fill="#FFFFFF")


def _wedding_card() -> dict:
    maroon, gold, ink = "#7A1F2B", "#B7791F", "#4A1D1F"
    return stage("Wedding invitation", 1200, 1680, "#FFF8EE", [
        R(48, 48, 1104, 1584, "none", stroke={"color": gold, "width": 4}, radius=24),
        R(72, 72, 1056, 1536, "none", stroke={"color": "#E7C98B", "width": 2}, radius=16)],
        F("Content", "column", [
            T("॥ श्री गणेशाय नमः ॥", 36, 400, maroon, font="Tiro Devanagari Hindi", align="center"),
            T("शुभ विवाह", 128, 400, maroon, font="Tiro Devanagari Hindi", align="center", lineHeight=1.2),
            T("Together with their families", 36, 500, ink, font="Cormorant Garamond", align="center", letterSpacing=2),
            F("Names", "column", [T("[Bride's name]", 104, 600, maroon, font="Cormorant Garamond", align="center", lineHeight=1.1),
                                  T("&", 64, 400, maroon, font="Cormorant Garamond", align="center"),
                                  T("[Groom's name]", 104, 600, maroon, font="Cormorant Garamond", align="center", lineHeight=1.1)],
              gap=8, align="center"),
            T("request the pleasure of your company at their wedding", 36, 400, ink, font="Cormorant Garamond", align="center",
              lineHeight=1.4, w=820),
            R(0, 0, 160, 3, gold, name="Rule"),
            F("When", "column", [T("[Day], [date]", 48, 600, ink, font="Cormorant Garamond", align="center"),
                                 T("[Time] · [Venue name]", 40, 500, ink, font="Cormorant Garamond", align="center"),
                                 T("[Venue address]", 36, 400, "#6B4A3A", font="Cormorant Garamond", align="center")], gap=12, align="center"),
            T("आपकी उपस्थिति प्रार्थनीय है", 40, 400, maroon, font="Tiro Devanagari Hindi", align="center"),
        ], pad=[160, 140, 160, 140], gap=48, align="center", justify="center"))


def _menu() -> dict:
    ink, accent, sub = "#1C1917", "#B45309", "#78716C"

    def dish(name: str, line: str) -> dict:
        return F("Dish", "row", [F("Text", "column", [T(name, 40, 600, ink, font="Fraunces"),
                                                      T(line, 28, 400, sub, font="Inter")], gap=6, w="fill"),
                                 T("₹[price]", 34, 600, accent, font="Inter")], gap=24, align="start")

    def section(title: str, dishes: list[tuple[str, str]]) -> dict:
        return F(title, "column", [F("Head", "row", [T(title, 52, 600, accent, font="Fraunces"),
                                                     {"type": "line", "color": "#E7D7C1", "width": 2, "w": "fill"}], gap=24, align="center"),
                                   *[dish(n, d) for n, d in dishes]], gap=36)
    return F("Restaurant menu", "column", [
        F("Header", "column", [T("[Restaurant name]", 104, 700, ink, font="Fraunces", align="center"),
                               T("MENU", 32, 600, accent, font="Inter", align="center", letterSpacing=12)], gap=16, align="center"),
        F("Columns", "row", [
            F("Left", "column", [section("Starters", [("Paneer tikka", "Smoky cottage cheese, mint chutney"),
                                                      ("Veg spring rolls", "Crisp rolls, sweet chilli dip"),
                                                      ("Masala papad", "Onion, tomato, chaat masala")]),
                                 section("Breads", [("Butter naan", "From the tandoor"), ("Lachha paratha", "Flaky, layered")])],
              gap=80, w="fill"),
            F("Right", "column", [section("Main course", [("Dal makhani", "Slow-cooked black lentils"),
                                                          ("Paneer butter masala", "Rich tomato gravy"),
                                                          ("Veg biryani", "Basmati rice, raita")]),
                                  section("Desserts", [("Gulab jamun", "Two pieces, warm"), ("Kulfi", "Kesar pista")])],
              gap=80, w="fill"),
        ], gap=80),
        F("Footer", "column", [T("[your address] · [phone number]", 30, 500, sub, font="Inter", align="center"),
                               T("Prices [include / do not include] taxes", 24, 400, sub, font="Inter", align="center")],
          gap=8, align="center"),
    ], w=1240, h=1754, pad=[120, 96, 96, 96], gap=80, justify="between", fill="#FFFBF5")


def _login_screen() -> dict:
    accent, ink, sub = "#4F46E5", "#0F172A", "#64748B"
    field = F("Mobile field", "row", [T("+91", 16, 600, ink), {"type": "rect", "w": 1, "h": 24, "fill": "#CBD5E1"},
                                      T("Mobile number", 16, 400, "#64748B", w="fill")],
              gap=12, align="center", pad=[0, 16, 0, 16], h=56, radius=14, fill="#FFFFFF", stroke={"color": "#CBD5E1", "width": 1})
    return F("Login", "column", [
        F("Top", "column", [
            F("Logo", "row", [I("sparkle", 32, "#FFFFFF", filled=True)], justify="center", align="center", w=64, h=64, radius=20,
              fill={"from": "#6366F1", "to": "#4338CA", "angle": 135}),
            F("Hello", "column", [T("Welcome back", 32, 700, ink, font="Plus Jakarta Sans"),
                                  T("Sign in with your mobile number. We will send you a one-time code.", 16, 400, sub,
                                    font="Plus Jakarta Sans", lineHeight=1.5)], gap=8)], gap=32),
        F("Form", "column", [T("Mobile number", 14, 600, ink, font="Plus Jakarta Sans"), field,
                             F("Button", "row", [T("Get code", 16, 600, "#FFFFFF", font="Plus Jakarta Sans")], justify="center",
                               align="center", h=56, radius=14, fill=accent),
                             F("Or", "row", [{"type": "line", "color": "#E2E8F0", "w": "fill"}, T("or", 14, 500, "#64748B"),
                                             {"type": "line", "color": "#E2E8F0", "w": "fill"}], gap=12, align="center"),
                             F("Email", "row", [I("mail", 20, ink), T("Continue with email", 16, 600, ink, font="Plus Jakarta Sans")],
                               gap=8, justify="center", align="center", h=56, radius=14, fill="#FFFFFF",
                               stroke={"color": "#CBD5E1", "width": 1})], gap=16, h="fill"),
        T("By continuing you agree to the Terms and the Privacy Policy.", 12, 400, "#64748B", font="Plus Jakarta Sans",
          align="center", w="fill"),
    ], w=390, h=844, pad=[72, 24, 40, 24], gap=40, fill="#F8FAFC")


def _home_screen() -> dict:
    accent, ink, sub = "#C2410C", "#1C1917", "#57534E"

    def tile(icon: str, label: str) -> dict:
        return F(label, "column", [F("Icon", "row", [I(icon, 24, accent)], justify="center", align="center", w=56, h=56, radius=16,
                                     fill="#FFEDD5"), T(label, 12, 500, ink)], gap=8, align="center", w="fill")

    def card(label: str) -> dict:
        return F("Card", "row", [IMG(label, w=88, h=88, radius=16, fill="#FFEDD5"),
                                 F("Text", "column", [T("[Item name]", 16, 600, ink), T("[Short detail]", 14, 400, sub),
                                                      T("₹[price]", 16, 700, accent)], gap=4, w="fill"),
                                 F("Add", "row", [I("plus", 20, "#FFFFFF")], justify="center", align="center", w=40, h=40, radius=999,
                                   fill=accent)],
                 gap=16, align="center", pad=12, radius=20, fill="#FFFFFF", shadow="sm")

    def nav(icon: str, label: str, on: bool = False) -> dict:
        c = accent if on else "#78716C"
        return F(label, "column", [I(icon, 24, c), T(label, 12, 600 if on else 500, c)], gap=4, align="center", w="fill")
    return F("Home", "column", [
        F("Content", "column", [
            F("Header", "row", [F("Hi", "column", [T("Good morning", 14, 400, sub), T("Hello, [Name]", 22, 700, ink, font="Outfit")], gap=2, w="fill"),
                                F("Bell", "row", [I("bell", 22, ink)], justify="center", align="center", w=44, h=44, radius=999, fill="#FFFFFF",
                                  shadow="sm")], align="center"),
            F("Search", "row", [I("search", 20, "#78716C"), T("Search for food, groceries…", 15, 400, "#78716C", w="fill")],
              gap=12, align="center", pad=[0, 16, 0, 16], h=52, radius=16, fill="#FFFFFF", stroke={"color": "#E7E5E4", "width": 1}),
            F("Promo", "row", [F("Text", "column", [T("[Offer title]", 22, 700, "#FFFFFF", font="Outfit"),
                                                    T("On your first order", 14, 400, "#FFEDD5"),
                                                    F("Btn", "row", [T("Order now", 14, 600, "#9A3412")], pad=[8, 16, 8, 16], radius=999,
                                                      fill="#FFFFFF", w="hug")], gap=8, w="fill"),
                               I("gift", 64, "#FFEDD5")], align="center", gap=16, pad=20, radius=24,
              fill={"from": "#C2410C", "to": "#7C2D12", "angle": 135}),
            F("Categories", "row", [tile("bag", "Grocery"), tile("gift", "Sweets"), tile("heart", "Health"), tile("truck", "Delivery")], gap=12),
            F("Popular", "column", [F("Head", "row", [T("Popular near you", 18, 700, ink, font="Outfit"), T("See all", 14, 600, accent)],
                                      justify="between", align="center"), card("Dish photo"), card("Dish photo")], gap=12),
        ], gap=20, pad=[56, 20, 16, 20], h="fill"),
        F("Tab bar", "row", [nav("home", "Home", True), nav("search", "Search"), nav("cart", "Cart"), nav("user", "Profile")],
          pad=[12, 16, 28, 16], fill="#FFFFFF", stroke={"color": "#E7E5E4", "width": 1}),
    ], w=390, h=844, fill="#FAFAF9")


def _pitch_slide() -> dict:
    def cell(n: str, title: str, line: str) -> dict:
        return F(title, "column", [T(n, 24, 600, "#A5B4FC", font="Space Grotesk", letterSpacing=2),
                                   T(title, 40, 700, "#FFFFFF", font="Space Grotesk"),
                                   T(line, 26, 400, "#C7D2FE", font="Inter", lineHeight=1.45)],
                 gap=16, pad=40, radius=24, fill="#1E1B4B", stroke={"color": "#3730A3", "width": 2}, w="fill", h="fill")
    return stage("Pitch slide", 1920, 1080, "#0B0B1F", [
        E(1240, -360, 1000, 1000, "#4F46E5", opacity=0.35), E(1500, 600, 700, 700, "#DB2777", opacity=0.18)],
        F("Content", "column", [
            F("Head", "column", [T("PITCH DECK · [YEAR]", 24, 600, "#A5B4FC", font="Inter", letterSpacing=6),
                                 T("[Company name]", 112, 700, "#FFFFFF", font="Space Grotesk", letterSpacing=-3, lineHeight=1.05),
                                 T("[What you do, for whom, in one line]", 40, 400, "#C7D2FE", font="Inter", w=1200)], gap=24),
            F("Grid", "row", [cell("01", "Problem", "[The pain your customers feel today, in one or two lines]"),
                              cell("02", "Solution", "[How your product removes that pain]"),
                              cell("03", "Why now", "[What changed that makes this the right time]")], gap=32, h=340),
            F("Footer", "row", [T("[Your name] · [Founder]", 26, 500, "#C7D2FE", font="Inter"),
                                T("[email]", 26, 500, "#C7D2FE", font="Inter")], justify="between"),
        ], pad=120, justify="between"))


def _youtube_thumb() -> dict:
    yellow = "#FACC15"
    return stage("YouTube thumbnail", 1280, 720, "#0A0A0A", [
        IMG("Your face or product, cut out", x=700, y=0, w=580, h=720, fill="#262626"),
        R(0, 0, 820, 720, {"from": "#0A0A0A", "to": "#171717", "angle": 90})],
        F("Content", "column", [
            T("WATCH THIS", 136, 400, "#FFFFFF", font="Bebas Neue", lineHeight=0.95),
            F("Highlight", "row", [T("BEFORE YOU START", 104, 400, "#0A0A0A", font="Bebas Neue", lineHeight=1.0)],
              pad=[8, 24, 0, 24], fill=yellow, w="hug"),
            T("[Your channel name]", 32, 600, "#D4D4D4", font="Inter"),
        ], pad=[96, 80, 80, 72], gap=24, justify="center"))


def _certificate() -> dict:
    gold, ink, navy = "#A16207", "#1F2937", "#1E3A8A"
    return stage("Certificate", 1754, 1240, "#FFFDF7", [
        R(40, 40, 1674, 1160, "none", stroke={"color": navy, "width": 6}),
        R(64, 64, 1626, 1112, "none", stroke={"color": "#D6B66E", "width": 2}),
        E(1400, 880, 200, 200, "#D6B66E"), E(1416, 896, 168, 168, "#FFFDF7", stroke={"color": gold, "width": 3}),
        I("star", 72, gold, filled=True, x=1464, y=944)],
        F("Content", "column", [
            T("CERTIFICATE", 72, 700, navy, font="Playfair Display", align="center", letterSpacing=12),
            T("of achievement", 40, 400, gold, font="Playfair Display", align="center", letterSpacing=4),
            T("This certificate is proudly presented to", 32, 400, "#4B5563", font="Inter", align="center"),
            T("[Recipient's name]", 104, 600, ink, font="Playfair Display", align="center", lineHeight=1.15),
            T("for [the reason: a course completed, a prize won, a job well done]", 32, 400, "#4B5563", font="Inter", align="center", w=1100,
              lineHeight=1.45),
            F("Signatures", "row", [
                F("Sign 1", "column", [{"type": "line", "color": ink, "width": 2}, T("[Name]", 28, 600, ink, font="Inter", align="center"),
                                       T("[Title]", 22, 400, "#6B7280", font="Inter", align="center")], gap=12, w=380, align="center"),
                F("Date", "column", [{"type": "line", "color": ink, "width": 2}, T("[Date]", 28, 600, ink, font="Inter", align="center"),
                                     T("Date", 22, 400, "#6B7280", font="Inter", align="center")], gap=12, w=380, align="center"),
            ], gap=160, justify="center", pad=[48, 0, 0, 0]),
        ], pad=[150, 200, 150, 200], gap=32, align="center", justify="center"))


def _hiring_post() -> dict:
    accent = "#1D4ED8"
    return F("Hiring post", "column", [
        F("Top", "column", [pill("WE'RE HIRING", "#DBEAFE", "#1E40AF", 28, icon="user", font="Manrope"),
                            T("Join our team as a", 48, 500, "#334155", font="Manrope"),
                            T("[Job title]", 112, 700, "#0F172A", font="Manrope", lineHeight=1.05, letterSpacing=-2)], gap=24),
        F("Facts", "column", [info_row("map-pin", "[City] · [On site / remote]", "#1E293B", 32, accent, "Manrope"),
                              info_row("clock", "[Full time / part time]", "#1E293B", 32, accent, "Manrope"),
                              info_row("check", "[Experience you need]", "#1E293B", 32, accent, "Manrope")], gap=24),
        F("Apply", "row", [F("Text", "column", [T("Apply now", 40, 700, "#FFFFFF", font="Manrope"),
                                                T("Send your CV to [email]", 28, 400, "#DBEAFE", font="Manrope")], gap=8, w="fill"),
                           F("Go", "row", [I("arrow-right", 40, accent)], justify="center", align="center", w=96, h=96, radius=999,
                             fill="#FFFFFF")], align="center", gap=24, pad=[40, 48, 40, 48], radius=32, fill=accent),
    ], w=1080, h=1080, pad=96, justify="between", fill={"from": "#EFF6FF", "to": "#FFFFFF", "angle": 180})


def _holi_post() -> dict:
    blobs = [E(-120, -100, 520, 520, "#EC4899", opacity=0.55), E(620, -160, 600, 600, "#F59E0B", opacity=0.5),
             E(760, 640, 520, 520, "#22C55E", opacity=0.45), E(-180, 700, 560, 560, "#3B82F6", opacity=0.45),
             E(380, 820, 360, 360, "#A855F7", opacity=0.4)]
    return stage("Holi post", 1080, 1080, "#FFFFFF", blobs + [E(140, 140, 800, 800, "#FFFFFF", opacity=0.92)],
                 F("Content", "column", [
                     T("होली की शुभकामनाएँ", 72, 600, "#BE185D", font="Baloo 2", align="center"),
                     T("Happy Holi", 136, 700, "#1F2937", font="Baloo 2", align="center", lineHeight=1.0),
                     T("Colours, sweets and smiles to you and your family.", 32, 400, "#4B5563", font="Baloo 2", align="center",
                       lineHeight=1.4, w=600),
                     T("— [Your business name]", 32, 600, "#7C3AED", font="Baloo 2", align="center"),
                 ], pad=200, gap=24, align="center", justify="center"))


def _web_hero() -> dict:
    accent, ink, sub = "#047857", "#0B1F17", "#3F5B50"

    def feat(icon: str, title: str, line: str) -> dict:
        return F(title, "column", [F("Icon", "row", [I(icon, 28, accent)], justify="center", align="center", w=56, h=56, radius=16,
                                     fill="#D1FAE5"), T(title, 22, 700, ink, font="Manrope"),
                                   T(line, 17, 400, sub, font="Manrope", lineHeight=1.55)], gap=12, w="fill")
    return F("Landing page", "column", [
        F("Nav", "row", [T("[Your brand]", 24, 700, ink, font="Manrope"),
                         F("Links", "row", [T("About", 16, 500, sub, font="Manrope"), T("Services", 16, 500, sub, font="Manrope"),
                                            T("Contact", 16, 500, sub, font="Manrope")], gap=40, w="hug"),
                         F("Cta", "row", [T("Get in touch", 16, 600, "#FFFFFF", font="Manrope")], pad=[12, 24, 12, 24], radius=999,
                           fill=accent, w="hug")], justify="between", align="center", pad=[24, 120, 24, 120]),
        F("Hero", "row", [
            F("Text", "column", [pill("[A short line about you]", "#D1FAE5", "#065F46", 15, font="Manrope"),
                                 T("[Your main promise in one clear line]", 64, 700, ink, font="Manrope", lineHeight=1.1, letterSpacing=-1.5),
                                 T("[Two lines about who you help and how. Keep it simple and specific.]", 20, 400, sub, font="Manrope",
                                   lineHeight=1.6),
                                 F("Buttons", "row", [F("Primary", "row", [T("Get started", 17, 600, "#FFFFFF", font="Manrope"),
                                                                           I("arrow-right", 20, "#FFFFFF")], gap=8, align="center",
                                                        pad=[16, 28, 16, 28], radius=999, fill=accent, w="hug"),
                                                      F("Secondary", "row", [T("Learn more", 17, 600, ink, font="Manrope")],
                                                        pad=[16, 28, 16, 28], radius=999, fill="#FFFFFF",
                                                        stroke={"color": "#CBD5E1", "width": 1}, w="hug")], gap=16, w="hug")],
              gap=28, w="fill"),
            IMG("Your hero photo", w=560, h=480, radius=32, fill="#D1FAE5"),
        ], gap=80, align="center", pad=[56, 120, 96, 120]),
        F("Features", "row", [feat("check", "[Feature one]", "[One line about it]"), feat("clock", "[Feature two]", "[One line about it]"),
                              feat("shield", "[Feature three]", "[One line about it]")], gap=48, pad=[64, 120, 96, 120], fill="#F1F8F5"),
    ], w=1440, h=1024, fill="#FFFFFF")


# id -> (name, category, size label, maker, search words)
_LIST: list[tuple[str, str, str, Any, str]] = [
    ("shop-sale-poster", "Shop sale poster", "Posters", _sale_poster, "sale offer discount shop store a4 flyer"),
    ("diwali-poster", "Diwali greetings poster", "Festivals", _diwali_poster, "diwali deepavali festival hindi दीपावली offer"),
    ("eid-poster", "Eid Mubarak poster", "Festivals", _eid_poster, "eid mubarak ramadan festival urdu"),
    ("christmas-poster", "Christmas poster", "Festivals", _christmas_poster, "christmas xmas new year festival offer"),
    ("holi-post", "Holi Instagram post", "Festivals", _holi_post, "holi colours festival hindi होली instagram"),
    ("coaching-poster", "Coaching class poster", "Posters", _coaching_poster, "coaching tuition class admissions school education"),
    ("grand-opening-post", "Grand opening post", "Social media", _grand_opening, "instagram grand opening launch shop"),
    ("new-arrival-post", "New arrival post", "Social media", _new_arrival, "instagram product new arrival price shop"),
    ("offer-story", "Offer story", "Social media", _story_offer, "instagram story offer code today only"),
    ("whatsapp-status", "WhatsApp status: today's special", "Social media", _whatsapp_status, "whatsapp status daily special food shop order"),
    ("hiring-post", "We're hiring post", "Business", _hiring_post, "hiring job vacancy career instagram linkedin"),
    ("business-card", "Business card", "Business", _business_card, "visiting card business card contact"),
    ("wedding-invite", "Wedding invitation (Hindi + English)", "Invitations", _wedding_card, "wedding shaadi invitation card hindi शुभ विवाह"),
    ("restaurant-menu", "Restaurant menu", "Food", _menu, "menu restaurant cafe dhaba food price list"),
    ("app-login", "App sign-in screen", "App screens", _login_screen, "app login sign in otp mobile phone screen"),
    ("app-home", "App home screen", "App screens", _home_screen, "app home screen food delivery grocery phone"),
    ("pitch-slide", "Pitch deck title slide", "Presentations", _pitch_slide, "pitch deck slide startup presentation investors"),
    ("youtube-thumbnail", "YouTube thumbnail", "YouTube", _youtube_thumb, "youtube thumbnail video"),
    ("certificate", "Certificate of achievement", "Certificates", _certificate, "certificate award achievement course"),
    ("landing-page", "Landing page", "Websites", _web_hero, "website landing page hero web home page"),
]
TIDS = [t[0] for t in _LIST]
_LOCK = threading.Lock()
_BUILT: dict[str, dict] = {}


def spec_of(tid: str) -> dict:
    row = next((t for t in _LIST if t[0] == tid), None)
    if row is None:
        raise KeyError(tid)
    return {"frames": [row[3]()]}


def build(tid: str) -> dict:
    """{nodes (the whole document), root, w, h, layers, spec, fixed} for a built-in template, made once per process."""
    with _LOCK:
        if tid in _BUILT:
            return _BUILT[tid]
    raw = spec_of(tid)
    spec = ai.clean_spec(json.loads(json.dumps(raw)), None, {}, "")
    made = ai.build(spec, ai.id_maker(1), FIRST_PAGE, (0, 0), None, {}, "tpl")
    nodes = new_document("")
    nodes.update(made["nodes"])
    root = made["roots"][0]
    out = {"nodes": nodes, "root": root, "w": nodes[root].get("w"), "h": nodes[root].get("h"), "layers": len(made["nodes"]),
           "spec": spec, "fixed": made["fixed"], "dropped": spec.get("dropped", 0)}
    with _LOCK:
        _BUILT[tid] = out
    return out


def _row(t: tuple) -> dict:
    tid, name, cat, _, words = t
    b = build(tid)
    return {"id": tid, "name": name, "category": cat, "w": b["w"], "h": b["h"], "layers": b["layers"], "mine": False,
            "thumb": f"/api/design/templates/{tid}/thumb", "tags": words}


def _match(row: dict, q: str, category: str) -> bool:
    if category and row["category"].lower() != category.lower():
        return False
    if not q:
        return True
    hay = (row["name"] + " " + row["category"] + " " + row.get("tags", "")).lower()
    return all(w in hay for w in q.lower().split())


def listing(tenant: str, q: str = "", category: str = "") -> dict:
    q, category = str(q or "").strip()[:80], str(category or "").strip()[:40]
    built = [r for r in (_row(t) for t in _LIST) if _match(r, q, category)]
    mine = [r for r in mine_list(tenant) if _match(r, q, category)]
    return {"templates": built, "mine": mine, "categories": list(CATEGORIES)}


# =============================================================================================== a new file from one
def _new_file(tenant: str, name: str, nodes_json: str, count: int, next_cid: int) -> dict:
    """design_files row like store.create_file, but with the client-number counter the copied ids need."""
    from ..db import session
    from . import store
    from .models import DesignFile, ensure_tables
    ensure_tables()
    with session() as s:
        row = DesignFile(tenant_id=tenant, name=store.clean_name(name), snapshot=store.pack(nodes_json), node_count=count,
                         next_cid=max(1, int(next_cid)))
        s.add(row)
        s.flush()
        return store._file(row)


def _next_cid_of(tenant: str, file_id: str) -> int:
    """The file's next client number: a copy of its ids must start its own counter there."""
    from ..db import session
    from .models import DesignFile, ensure_tables
    ensure_tables()
    with session() as s:
        row = s.get(DesignFile, file_id)
        return int(row.next_cid or 1) if row is not None and row.tenant_id == tenant else 1


def use(tenant: str, tid: str, name: str = "") -> dict:
    """A NEW file in HER files from a template (built-in or one of her own). KeyError = no such template for her."""
    tid = str(tid or "").strip()
    if tid.startswith("mine_"):
        meta, doc_json = mine_get(tenant, tid)
        count = len((loads(doc_json).get("nodes") or {}))
        return _new_file(tenant, name or meta["name"], doc_json, count, int(meta.get("next_cid") or 1))
    if tid not in TIDS:
        raise KeyError(tid)
    b = build(tid)
    label = next(t[1] for t in _LIST if t[0] == tid)
    nodes = json.loads(json.dumps(b["nodes"]))                     # every file gets its own copy
    nodes[b["root"]]["aiSettle"] = f"{int(time.time() * 1000):x}"
    return _new_file(tenant, name or label, dumps_nodes(nodes), len(nodes), 2)


# =============================================================================================== her own templates
def _mine_dir(tenant: str) -> Path:
    from .assets import _tenant_dir
    return _tenant_dir(tenant) / "templates"


_MINE_ID = re.compile(r"^mine_[0-9a-f]{16}$")


def mine_list(tenant: str) -> list[dict]:
    folder = _mine_dir(tenant)
    if not folder.is_dir():
        return []
    out = []
    for p in sorted(folder.glob("mine_*.json")):
        try:
            meta = json.loads(p.read_text("utf-8")).get("meta") or {}
        except (OSError, ValueError):
            continue
        if _MINE_ID.match(str(meta.get("id") or "")):
            out.append({**meta, "mine": True, "thumb": f"/api/design/templates/{meta['id']}/thumb"})
    return sorted(out, key=lambda r: r.get("created_at") or "", reverse=True)


def mine_get(tenant: str, tid: str) -> tuple[dict, str]:
    if not _MINE_ID.match(tid or ""):
        raise KeyError(tid)
    path = _mine_dir(tenant) / f"{tid}.json"
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        raise KeyError(tid) from None
    return data["meta"], data["doc"]


def publish(tenant: str, file: dict, doc_json: str, next_cid: int, name: str, category: str) -> dict:
    """Keep HER file as one of HER templates (never public; reviewed False). ValueError = refused, said plainly."""
    from . import assets
    if len(doc_json) > MINE_BYTES:
        raise ValueError("This file is too large to keep as a template.")
    nodes = (loads(doc_json).get("nodes") or {})
    if len(nodes) > MINE_NODES:
        raise ValueError(f"A template can hold up to {MINE_NODES:,} layers; this file has {len(nodes):,}.")
    if not any(n.get("parent") in {p for p, pn in nodes.items() if pn.get("type") == "PAGE"} for n in nodes.values()):
        raise ValueError("This file is empty: draw something on it first.")
    if len(mine_list(tenant)) >= MINE_MAX:
        raise ValueError(f"You can keep up to {MINE_MAX} of your own templates; delete one first.")
    cat = next((c for c in CATEGORIES if c.lower() == str(category or "").strip().lower()), "My designs")
    tid = "mine_" + secrets.token_hex(8)
    frame = _first_frame(nodes)
    meta = {"id": tid, "name": " ".join(str(name or file.get("name") or "My template").split())[:80] or "My template",
            "category": cat, "reviewed": False, "public": False, "source": file["id"],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "layers": len(nodes),
            "next_cid": int(next_cid or 1), "w": (nodes.get(frame) or {}).get("w"), "h": (nodes.get(frame) or {}).get("h")}
    folder = _mine_dir(tenant)
    folder.mkdir(parents=True, exist_ok=True)
    png = assets.thumb_path(tenant, file["id"])
    if png.is_file():
        assets._write(folder / f"{tid}.png", png.read_bytes())
    assets._write(folder / f"{tid}.json", json.dumps({"meta": meta, "doc": doc_json}).encode("utf-8"))
    return {**meta, "mine": True, "thumb": f"/api/design/templates/{tid}/thumb"}


def mine_delete(tenant: str, tid: str) -> bool:
    if not _MINE_ID.match(tid or ""):
        return False
    folder, hit = _mine_dir(tenant), False
    for ext in ("json", "png"):
        p = folder / f"{tid}.{ext}"
        if p.is_file():
            p.unlink()
            hit = True
    return hit


# =============================================================================================== SVG thumbnails
def _first_frame(nodes: dict[str, dict]) -> str:
    pages = sorted((p for p, n in nodes.items() if n.get("type") == "PAGE" and n.get("parent") == ROOT),
                   key=lambda p: (nodes[p].get("idx", ""), p))
    for page in pages:
        kids = sorted((k for k, n in nodes.items() if n.get("parent") == page and n.get("visible") is not False),
                      key=lambda k: (nodes[k].get("idx", ""), k))
        if kids:
            return next((k for k in kids if nodes[k].get("type") in ("FRAME", "COMPONENT")), kids[0])
    return ""


def _num(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else d


class _Svg:
    def __init__(self, nodes: dict[str, dict]):
        self.nodes = nodes
        self.kids: dict[str, list[str]] = {}
        for nid, n in nodes.items():
            if isinstance(n.get("parent"), str):
                self.kids.setdefault(n["parent"], []).append(nid)
        for k in self.kids.values():
            k.sort(key=lambda c: (nodes[c].get("idx", ""), c))
        self.defs: list[str] = []
        self.n = 0

    def _paint(self, fills: Any, x: float, y: float, w: float, h: float) -> tuple[str, float] | None:
        for p in reversed(fills if isinstance(fills, list) else []):
            if not isinstance(p, dict) or p.get("visible") is False:
                continue
            op = _num(p.get("opacity"), 1.0)
            if p.get("type") == "solid" and ai.color(p.get("color")):
                return ai.color(p["color"]), op
            if p.get("type") in ("linear", "radial") and p.get("stops"):
                self.n += 1
                gid = f"g{self.n}"
                stops = "".join(f'<stop offset="{_num(s.get("pos")):.3f}" stop-color="{ai.color(s.get("color")) or "#000000"}" '
                                f'stop-opacity="{_num(s.get("opacity"), 1.0):.3f}"/>' for s in p["stops"] if isinstance(s, dict))
                if p["type"] == "linear":
                    f, t = p.get("from") or [0.5, 0], p.get("to") or [0.5, 1]
                    self.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x + _num(f[0]) * w:.1f}" '
                                     f'y1="{y + _num(f[1]) * h:.1f}" x2="{x + _num(t[0]) * w:.1f}" y2="{y + _num(t[1]) * h:.1f}">{stops}</linearGradient>')
                else:
                    self.defs.append(f'<radialGradient id="{gid}">{stops}</radialGradient>')
                return f"url(#{gid})", op
            if p.get("type") == "image":
                return "#D4D4D8", op
        return None

    def _lines(self, n: dict, w: float) -> list[str]:
        chars = str(n.get("chars") or "")
        if n.get("textCase") == "upper":
            chars = chars.upper()
        font, size = str(n.get("font") or "Inter"), _num(n.get("fontSize"), 16)
        weight, ls = _num(n.get("fontWeight"), 400), _num(n.get("letterSpacing"), 0)
        wrap = n.get("autoResize", "wh") != "wh" and w > 0
        out: list[str] = []
        for para in chars.split("\n"):
            if not wrap:
                out.append(para)
                continue
            line = ""
            for word in para.split(" "):
                trial = (line + " " + word) if line else word
                if line and ailayout.text_width(trial, font, size, weight, ls) > w + 0.5:
                    out.append(line)
                    line = word
                else:
                    line = trial
            out.append(line)
        return out

    def node(self, nid: str, ox: float, oy: float, out: list[str], depth: int = 0) -> None:
        n = self.nodes.get(nid) or {}
        if n.get("visible") is False or depth > 40:
            return
        x, y = ox + _num(n.get("x")), oy + _num(n.get("y"))
        w, h = _num(n.get("w"), 0), _num(n.get("h"), 0)
        kind = n.get("type")
        op = _num(n.get("opacity"), 1.0)
        group = f'<g opacity="{op:.2f}">' if op < 1 else ""
        if group:
            out.append(group)
        r = n.get("radius")
        rad = min(_num(r if not isinstance(r, list) else (r[0] if r else 0)), w / 2, h / 2)
        stroke = self._paint(n.get("strokes"), x, y, w, h) if kind != "TEXT" else None
        sw = _num(n.get("strokeWeight"), 1)
        sattr = f' stroke="{stroke[0]}" stroke-opacity="{stroke[1]:.2f}" stroke-width="{sw:.1f}"' if stroke else ""
        if kind in ("FRAME", "RECT", "COMPONENT", "INSTANCE", "SECTION"):
            fill = self._paint(n.get("fills"), x, y, w, h)
            if fill or stroke:
                inset = sw / 2 if stroke else 0
                out.append(f'<rect x="{x + inset:.1f}" y="{y + inset:.1f}" width="{max(0, w - 2 * inset):.1f}" height="{max(0, h - 2 * inset):.1f}" '
                           f'rx="{rad:.1f}" fill="{fill[0] if fill else "none"}" fill-opacity="{fill[1] if fill else 1:.2f}"{sattr}/>')
        elif kind == "ELLIPSE":
            fill = self._paint(n.get("fills"), x, y, w, h)
            out.append(f'<ellipse cx="{x + w / 2:.1f}" cy="{y + h / 2:.1f}" rx="{w / 2:.1f}" ry="{h / 2:.1f}" '
                       f'fill="{fill[0] if fill else "none"}" fill-opacity="{fill[1] if fill else 1:.2f}"{sattr}/>')
        elif kind == "VECTOR" and isinstance(n.get("path"), str) and re.fullmatch(r"[MLCZmlcz0-9.\s,-]*", n["path"]):
            fill = self._paint(n.get("fills"), x, y, w, h)
            extra = ' stroke-linecap="round" stroke-linejoin="round"' if stroke else ""
            out.append(f'<path transform="translate({x:.1f} {y:.1f})" d="{n["path"]}" fill="{fill[0] if fill else "none"}"{sattr}{extra}/>')
        elif kind == "TEXT":
            fill = self._paint(n.get("fills"), x, y, w, h) or ("#111827", 1.0)
            size = _num(n.get("fontSize"), 16)
            lh = _num(n.get("lineHeight"), size * 1.25)
            align = n.get("align") or "left"
            anchor, tx = {"center": ("middle", x + w / 2), "right": ("end", x + w)}.get(align, ("start", x))
            fam = _esc(str(n.get("font") or "Inter"), quote=True)
            serif = "serif" if re.search(r"serif|garamond|playfair|lora|fraunces|literata|merriweather|baskerville|crimson|tiro", fam, re.I) \
                and "sans" not in fam.lower() else "sans-serif"
            spans = "".join(f'<tspan x="{tx:.1f}" y="{y + i * lh + (lh - size) / 2 + size * 0.8:.1f}">{_esc(line)}</tspan>'
                            for i, line in enumerate(self._lines(n, w)))
            ls = _num(n.get("letterSpacing"), 0)
            out.append(f'<text font-family="\'{fam}\', {serif}" font-size="{size:.1f}" font-weight="{int(_num(n.get("fontWeight"), 400))}" '
                       f'fill="{fill[0]}" fill-opacity="{fill[1]:.2f}" text-anchor="{anchor}"'
                       + (f' letter-spacing="{ls:.1f}"' if ls else "") + f">{spans}</text>")
        if kind not in ("TEXT", "VECTOR", "ELLIPSE", "RECT", "LINE"):
            clip = ""
            if n.get("clip") and depth > 0 and kind in ("FRAME", "COMPONENT", "INSTANCE"):
                self.n += 1
                cid = f"c{self.n}"
                self.defs.append(f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rad:.1f}"/></clipPath>')
                clip = cid
            if clip:
                out.append(f'<g clip-path="url(#{clip})">')
            for k in self.kids.get(nid, []):
                self.node(k, x, y, out, depth + 1)
            if clip:
                out.append("</g>")
        if group:
            out.append("</g>")

    def render(self, root: str) -> str:
        n = self.nodes.get(root) or {}
        w, h = max(1.0, _num(n.get("w"), 100)), max(1.0, _num(n.get("h"), 100))
        body: list[str] = []
        self.node(root, -_num(n.get("x")), -_num(n.get("y")), body)
        scale = THUMB_W / max(w, h)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w * scale:.0f}" height="{h * scale:.0f}">'
                f'<defs>{"".join(self.defs)}</defs><clipPath id="root"><rect width="{w:.0f}" height="{h:.0f}"/></clipPath>'
                f'<g clip-path="url(#root)">{"".join(body)}</g></svg>')


_SVGS: dict[str, str] = {}


def thumb(tenant: str, tid: str) -> tuple[bytes, str]:
    """(bytes, media type) of a template's picture. KeyError = no such template for her."""
    if tid in TIDS:
        if tid not in _SVGS:
            b = build(tid)
            _SVGS[tid] = _Svg(b["nodes"]).render(b["root"])
        return _SVGS[tid].encode("utf-8"), "image/svg+xml"
    meta, doc_json = mine_get(tenant, tid)
    png = _mine_dir(tenant) / f"{tid}.png"
    if png.is_file():
        return png.read_bytes(), "image/png"
    nodes = loads(doc_json).get("nodes") or {}
    frame = _first_frame(nodes)
    if not frame:
        raise KeyError(tid)
    return _Svg(nodes).render(frame).encode("utf-8"), "image/svg+xml"


# =============================================================================================== routes
_IMG_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=600",
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"}


def mount(r, current_tenant) -> None:
    """The gallery routes on the design router (key + switch already checked by the router)."""
    from fastapi import Depends, HTTPException
    from fastapi.responses import Response

    from . import store
    from .room import HUB, bg

    @r.get("/templates")
    async def templates_list(q: str = "", category: str = "", tenant: str = Depends(current_tenant)):
        return await bg(listing, tenant, q, category)

    @r.get("/templates/{tid}/thumb")
    async def template_thumb(tid: str, tenant: str = Depends(current_tenant)):
        try:
            data, mime = await bg(thumb, tenant, tid)
        except KeyError:
            raise HTTPException(404, "Template not found") from None
        return Response(data, media_type=mime, headers=_IMG_HEADERS)

    @r.post("/templates/{tid}/use")
    async def template_use(tid: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        """A NEW file in her files from this template (her files are never changed)."""
        name = body.get("name") if isinstance(body, dict) and isinstance(body.get("name"), str) else ""
        try:
            return await bg(use, tenant, tid, name[:120])
        except KeyError:
            raise HTTPException(404, "Template not found") from None

    @r.delete("/templates/{tid}")
    async def template_delete(tid: str, tenant: str = Depends(current_tenant)):
        if not await bg(mine_delete, tenant, tid):
            raise HTTPException(404, "Template not found (only your own templates can be deleted)")
        return {"ok": True}

    @r.post("/files/{file_id}/publish-template")
    async def publish_template(file_id: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        """{name, category} -> HER file kept as one of HER templates: private to her account, reviewed False,
        never listed to anybody else. Only the file's own account can do this."""
        body = body if isinstance(body, dict) else {}
        file = await bg(store.get_file, tenant, file_id)
        if file is None or file.get("trashed"):
            raise HTTPException(404, "File not found")
        got = await HUB.read(file_id, tenant)
        if got is None:
            raise HTTPException(404, "File not found")
        try:
            return await bg(publish, tenant, file, got[1], await bg(_next_cid_of, tenant, file_id),
                            str(body.get("name") or "")[:120], str(body.get("category") or "")[:40])
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
