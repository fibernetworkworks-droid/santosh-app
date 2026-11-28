"""v0.999.334 BUSINESS SCREEN, NUMBER AND WORDING RULES - read from Ant Design's design specs (github.com/ant-design/
ant-design docs/spec, c046700, MIT) and written in Hoola's own words, for every country.

Ant Design is the design system behind a great deal of the world's admin consoles and dashboards. Its specs say how a
search-and-filter table, a step form, a record page, a dashboard, a settings page, a result page, an error page and an
empty state should work, how numbers / money / dates are shown, and how buttons and messages are worded. Hoola's own
UX rules (coder/uxrules.py) carry these beside the design database's rules, so the writers get them for what they are
building and the critic judges by them. Their defaults are China's (YYYY-MM-DD, ¥); here every rule follows the
business's own country and language.

Each rule has the shape of a design-database row (Issue / Do / Don't), so uxrules treats both the same.
"""
from __future__ import annotations

SOURCE = "Ant Design specs (github.com/ant-design/ant-design docs/spec, c046700, MIT), in Hoola's words"


def _r(issue: str, do: str, dont: str = "") -> dict[str, str]:
    return {"Issue": issue, "Do": do, "Don't": dont, "Platform": "All", "Source": "Ant Design"}


RULES: dict[str, list[dict[str, str]]] = {
    # what happens after she acts, and the pages that cannot show what was asked for
    "states": [
        _r("Result After Submit", "after a send, payment or order say object + action + result ('Order 1042 is placed'), "
           "what happens next, and at most 2 next buttons", "only 'Success!'"),
        _r("Error Says Why and the Way Out", "say what failed, that nothing was lost, and give Try again / Contact",
           "a bare error code or a dead end"),
        _r("Empty State With a Next Step", "say what goes here and give the first action (new user); 'Clear filters' "
           "when a search found nothing", "a blank area"),
        _r("Page Not Found and No Access", "404: the link may be old + Go home / Search; 403: who to ask; 500: work is "
           "safe + Try again"),
        _r("Loading Keeps the Shape", "show a skeleton of the layout while it loads; a failed load says so in place with "
           "Try again"),
        _r("Light Feedback Stays Light", "a small save gets a short note or toast, not a whole result page"),
    ],
    # the search-and-filter list ("query table") every business app is made of
    "tables": [
        _r("Filters Above the List", "a search box and the 2-4 most used filters above it, the rest under More filters, "
           "with Reset", "a wall of filter boxes"),
        _r("Row Actions", "1-2 row actions as text, the rest in a More menu", "a row of five icons"),
        _r("Bulk Actions When Rows Are Picked", "tick boxes; a bar with '3 selected' and what can be done to them",
           "bulk buttons always showing"),
        _r("Numbers Right-Aligned", "money and counts right-aligned, same decimals down a column"),
        _r("Paging Shows the Total", "show the total and the page; filters stay when the page changes"),
        _r("Status in Words", "status as a tag or dot with its word", "colour alone"),
    ],
    "detail": [
        _r("Header Says What and Where It Stands", "the record's name, its status and its 1-2 main actions at the top"),
        _r("Fields in Groups", "label-value pairs in titled groups, most used first", "one long list of fields"),
        _r("History Last", "changes and the timeline at the bottom or in their own tab"),
    ],
    "dashboard": [
        _r("Key Numbers First", "the main numbers on top, each with its period and a comparison ('vs last week')"),
        _r("Needs You First", "what waits for her decision comes before charts, each with its button"),
        _r("One Chart One Question", "a chart's title says what it answers; units and the period are shown"),
        _r("Big Numbers Short", "tiles show short numbers (1.2K, 12 lakh); the full number in the detail"),
    ],
    "settings": [
        _r("Settings in Groups", "titled groups; a line under each switch says what it does"),
        _r("Dangerous Last", "delete / close account at the bottom, set apart, asked again before it happens"),
    ],
    "long_forms": [
        _r("Steps for Long Tasks", "a long form in distinct parts becomes steps with a step bar; going back keeps "
           "what she typed"),
        _r("Related Fields Together", "fields in titled groups; two columns only for short related pairs"),
        _r("Main Button Where the Fields End", "the main button after the last field, Cancel beside it"),
        _r("Check Before Money Moves", "a summary to check before a payment or order is placed"),
    ],
    # numbers, money, dates - the data-format spec, in the business's own country
    "numbers": [
        _r("Digits in Groups", "group digits the country's way (12,34,567 in India, 1,234,567 in the US)"),
        _r("Currency the Country's Way", "the currency people know (₹, $, €) placed the country's way; the code (USD) "
           "when several currencies appear", "a fixed symbol for every country"),
        _r("Dates in Their Order", "the country's date order; the month as a word when it could be misread "
           "(3 Nov 2026); a range said once"),
        _r("Recent Times Relative", "'just now', '5 minutes ago', 'yesterday' for the last days, the date after that"),
        _r("Time and Zone", "24-hour or am/pm as the country reads it; the time zone named when people are in "
           "different zones"),
        _r("Units and Percents", "a short unit with the number (12 kg, 5 km); percents with at most one decimal"),
    ],
    # wording and buttons - the copywriting and button specs
    "words": [
        _r("Button Says the Action", "verb + object ('Save changes', 'Send invoice')", "'Submit', 'OK', 'Click here'"),
        _r("One Main Button per Area", "one main action per form, card or dialog; the rest plain or text buttons"),
        _r("Their Words, Their Side", "'Your orders' in the words customers use", "internal names or system terms"),
        _r("Important First", "the key fact at the start of the line"),
        _r("Calm Tone", "say what to do ('The number needs 10 digits')", "blame or exclamation marks"),
        _r("Same Thing Same Word", "one name for a thing on every screen"),
        _r("Danger Looks Different", "a destructive button in the danger colour, asked again before it acts"),
    ],
}


def rules(topic: str) -> list[dict[str, str]]:
    return list(RULES.get(topic) or [])
