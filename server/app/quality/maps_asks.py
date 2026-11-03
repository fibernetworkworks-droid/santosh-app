"""v0.470 Phase 11 PROOF - the MAPS card's ask set: real geographic asks with an answer that can be CHECKED.

The honesty rule of this set, and the reason it looks the way it does: a geographic "right answer" must never be a
fact remembered about the world (how far Akola is from Nagpur, where a station stands). Nothing here is remembered.
Every row is checkable one of three ways:

- kind "geo"   - the ask CARRIES its own coordinates, so the right answer is ARITHMETIC. `mapscard` computes the key
                 itself with the same haversine the server uses; the set stores no answer at all. Points are chosen
                 far enough apart that the straight-line winner is also the road winner (a near-tie would make the
                 card lie about a correct road answer).
- kind "tool"  - the ask is scored on the TOOL, not on a fact: which of the 20 maps / listing / own-map tools is the
                 right first pick, and which families must NOT be in view. This is what measures whether Phases 4-10
                 are reachable at all from her words.
- kind "rule"  - a licence or money guard that MUST hold, scored in code: a lead list is refused and WHY is said, a
                 map in a PDF comes out as a link and never a picture, the day's plan only proposes, a place with no
                 solar imagery is "not covered", the daily cap refuses before it spends.

MAPS_SET_V moves only with a deliberate change to the set.
"""
from __future__ import annotations

MAPS_SET_V = 1

# Four points around Akola / Amravati / Nagpur, given to the ASK itself. They are inputs, not claims about the
# world: the card only ever asserts which of them is nearest to another given point, which is arithmetic.
P = {
    "a": {"name": "Godown A", "lat": 20.70, "lng": 77.00},
    "b": {"name": "Godown B", "lat": 20.95, "lng": 77.75},
    "c": {"name": "Godown C", "lat": 21.15, "lng": 79.09},
    "d": {"name": "Godown D", "lat": 19.87, "lng": 75.34},
}
HERE = {"lat": 20.74, "lng": 77.05}        # the asking point for the geo rows

PC = ("pc",)

ASKS: list[dict] = [
    # ---------------------------------------------------------------- geo: the answer is arithmetic (no world facts)
    {"id": "geo_nearest_of_four", "kind": "geo", "check": "nearest",
     "points": [P["a"], P["b"], P["c"], P["d"]], "from": HERE,
     "text": ("Mere chaar godown hain: Godown A 20.70,77.00 · Godown B 20.95,77.75 · Godown C 21.15,79.09 · "
              "Godown D 19.87,75.34. Main 20.74,77.05 par hoon - inmein se sabse paas kaun hai?"),
     "ok": ["maps_nearest"], "bad": PC},
    # a DISTANCE, not a name: the straight line is said in the ask, so the arithmetic answer is the asked answer
    {"id": "geo_straight_km", "kind": "geo", "check": "km",
     "points": [P["c"]], "from": HERE,
     "text": "20.74,77.05 se 21.15,79.09 ki seedhi doori (straight line) kitne km hai?",
     "ok": ["pylab", "maps_nearest", "maps_directions"], "bad": PC},
    {"id": "geo_within_radius", "kind": "geo", "check": "within", "radius_km": 150,
     "points": [P["a"], P["b"], P["c"], P["d"]], "from": HERE,
     "text": ("Yeh meri jagahen hain: Godown A 20.70,77.00, Godown B 20.95,77.75, Godown C 21.15,79.09, "
              "Godown D 19.87,75.34. 20.74,77.05 se seedhi doori mein 150 km ke andar kaun kaun aati hain? "
              "Naam batao."),
     "ok": ["maps_nearest", "ownmap_near", "pylab"], "bad": PC},
    {"id": "geo_order_of_three", "kind": "geo", "check": "order",
     "points": [P["b"], P["c"], P["d"]], "from": HERE,
     "text": ("20.74,77.05 se in teeno ko seedhi doori ke hisaab se paas se door ke kram mein lagao: "
              "Godown C 21.15,79.09, Godown D 19.87,75.34, Godown B 20.95,77.75."),
     "ok": ["maps_nearest", "pylab"], "bad": PC},

    # ---------------------------------------------------------------- tool: is each phase reachable from her words?
    {"id": "tool_category_near", "kind": "tool", "text": "Mere paas koi chemist hai kya, 2 km ke andar?",
     "ok": ["maps_nearby"], "bad": PC},
    {"id": "tool_named_place", "kind": "tool", "text": "Haldiram Nagpur ka address aur phone number do",
     "ok": ["maps_search", "maps_place"], "bad": PC},
    {"id": "tool_one_place_detail", "kind": "tool", "text": "Us pharmacy ka phone aur timing batao jo abhi list mein aayi thi",
     "ok": ["maps_place", "maps_nearby", "maps_search"], "bad": PC},
    {"id": "tool_time_distance", "kind": "tool", "text": "Akola se Amravati jaane mein kitna time lagega abhi?",
     "ok": ["maps_directions"], "bad": PC},
    {"id": "tool_nearest_worker", "kind": "tool",
     "text": "Mere 5 field workers mein se kaun is customer ke sabse paas hai, road se?",
     "ok": ["maps_nearest"], "bad": PC},
    {"id": "tool_day_route", "kind": "tool",
     "text": "Aaj ke 12 delivery kis kram mein karun? Do customers ne 10 se 12 ka time diya hai.",
     "ok": ["maps_route_plan"], "bad": PC},
    {"id": "tool_address_check", "kind": "tool",
     "text": "Yeh address bhejne layak hai ya galat hai: 'Near Ram Mandir, Tilak Road, Akola 444001'?",
     "ok": ["maps_address_check"], "bad": PC},
    {"id": "tool_reverse", "kind": "tool", "text": "Driver ne 20.705,77.012 bheja hai - yeh kaunsi jagah hai?",
     "ok": ["maps_pata"], "bad": PC},
    {"id": "tool_map_in_pdf", "kind": "tool",
     "text": "Quotation PDF mein hamari dukaan ka map bhi daal do taaki customer pahunch jaaye",
     "ok": ["maps_links", "doc_studio"], "bad": PC},
    {"id": "tool_my_listing", "kind": "tool", "text": "Google par meri dukaan ki listing mein kya kya likha hai abhi?",
     "ok": ["gbp_locations"], "bad": PC},
    {"id": "tool_listing_numbers", "kind": "tool",
     "text": "Pichhle 30 din mein Google se kitne log meri dukaan tak pahunche?",
     "ok": ["gbp_numbers"], "bad": PC},
    {"id": "tool_own_pins", "kind": "tool",
     "text": "My Maps se export ki hui KML file daal rahi hoon, isko Hoola mein le lo",
     "ok": ["ownmap_import"], "bad": PC},
    {"id": "tool_own_near", "kind": "tool", "text": "Mere save kiye pins mein se Tilak Road ke paas kaun kaun hain?",
     "ok": ["ownmap_near"], "bad": PC},
    {"id": "tool_solar", "kind": "tool", "text": "Meri chhat par solar lag sakta hai kya, kitne panel aayenge?",
     "ok": ["solar_check"], "bad": PC},
    {"id": "tool_gps_trail", "kind": "tool",
     "text": "Driver ke phone ka GPS trail tedha-medha aa raha hai, usko road par set kar do",
     "ok": ["maps_snap"], "bad": PC},
    {"id": "tool_cost", "kind": "tool", "text": "Aaj Google Maps ka kitna kharcha hua?",
     "ok": ["maps_kharcha"], "bad": PC},
    {"id": "tool_navigate", "kind": "tool", "text": "Is address tak navigation chalu kar do mere phone par",
     "ok": ["maps_navigate", "maps_directions"], "bad": PC},

    # ---------------------------------------------------------------- rule: the guards the whole plan rests on
    {"id": "rule_lead_list", "kind": "rule", "guard": "refuse_lead_list",
     "text": ("Akola ke saare hardware shops ki list Excel mein nikaal do - naam, address, phone - 200 shops, "
              "main unko marketing calls karungi"),
     "ok": ["maps_nearby", "indiamart_khoj", "data_fetch"], "bad": PC},
    {"id": "rule_map_picture", "kind": "rule", "guard": "link_not_picture",
     "text": "Dukaan ka Google map ka screenshot nikaal kar PDF mein chipka do",
     "ok": ["maps_links", "doc_studio"], "bad": PC},
    {"id": "rule_plan_only", "kind": "rule", "guard": "plan_proposes_only",
     "text": "Aaj ke 8 delivery ka rasta bana kar driver ko assign bhi kar do",
     "ok": ["maps_route_plan"], "bad": PC},
    {"id": "rule_solar_unknown", "kind": "rule", "guard": "solar_not_covered",
     "text": "Is gaon ki chhat par solar ka hisaab do: 19.6411,76.1372",
     "ok": ["solar_check"], "bad": PC},
    {"id": "rule_cap", "kind": "rule", "guard": "cap_refuses",
     "text": "Maps ka aaj ka budget khatam ho gaya hai to bhi 50 jagah ka data nikaalo",
     "ok": ["maps_kharcha", "maps_nearby"], "bad": PC},
]
