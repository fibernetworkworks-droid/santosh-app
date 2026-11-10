"""v0.757 KALA KHULA: the google/skills catalog tool (`kala`, v0.681) is reached by everyday Google Cloud words -
it had none of its own, so 'GKE cluster kaise banaun' / 'bigquery mein ML model' never brought it into view - and
its own name (Hindi kala = black / art) no longer opens it ('kala kurta order karo')."""
from __future__ import annotations

from app.agent import admit
from app.agent.kala_tools import KALA_TOOLS
from app.config import get_settings

POS = ["google cloud par GKE cluster kaise banaun", "gemini api kaise use karu apne app mein",
       "bigquery mein ml model kaise banaye", "google ki official skill dikhao cloud run deploy ke liye",
       "firebase setup kaise kare", "is gcp IAM error ko kaise fix karu permission denied",
       "vertex ai agent kaise deploy kare", "google cloud logging query likhni hai",
       "spanner vs alloydb kaunsa lu", "admob ads app mein kaise lagaun"]
NEG = ["google pe search karo aaj ka mausam", "meri photo black and white kar do", "google drive mein file daalo",
       "kal meeting hai calendar mein daalo", "google maps pe raasta batao", "gmail check karo",
       "kala kurta online order karo", "cloud jaisa soft pillow chahiye"]


def _has(q):
    a = admit.plan_for(q, get_settings())
    return a is not None and "kala" in a.families


def test_google_cloud_asks_bring_kala(env):
    assert [q for q in POS if not _has(q)] == []


def test_unrelated_asks_leave_it_out(env):
    assert [q for q in NEG if _has(q)] == []


def test_description_names_the_products():
    d = KALA_TOOLS[0]["description"]
    for w in ("GKE", "BigQuery", "Vertex AI", "Gemini API", "Firebase", "Cloud Run"):
        assert w in d
