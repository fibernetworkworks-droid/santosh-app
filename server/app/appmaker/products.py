"""v0.138 PRODUCT / consumer apps: apps that are a product of their own (a music streaming app, an OTT, a short-video app, a
chat app, a ride app, a food-delivery marketplace ...), not "the app of a shop". Before this every request was squeezed
into the 1,000 local-business types, so "Spotify jaisa music sunne ka app" became a musical-instruments shop and the
owner's own business (an ISP) filled the screens.

Each product = an app goal (same shape as taxonomy.GOALS: screens, tabs, flow, words, brief) + what the blueprint needs
(modules, roles, level preset, phone features, login) + its own store / India rules, moods, questions, and a pseudo
business type `app_<id>` so the library, brief, plan and build work unchanged.

`match(text)` reads her words: a brand she names ("Spotify jaisa", "like Netflix") is only a REFERENCE for the kind of app
(never its name / logo / colours / layout); product phrases ("gaane sunne ka app", "music streaming", "short video app")
count by length; words that say she means a business ("music classes", "meri dukaan", "instrument shop") switch a product
off unless she named a brand.

Pure data + a matcher: taxonomy imports this file, never the other way round."""
from __future__ import annotations

import re
from typing import Any

PRODUCT_RULES: dict[str, str] = {
    "music_licence": "Music: only songs she owns or has licensed (labels / publishers, IPRS / PPL / Novex style licences) or royalty-free "
                     "tracks; sample tracks are marked [demo]. Selling a subscription for songs inside the app = digital content -> "
                     "Google Play Billing / Apple in-app purchase.",
    "ott_code": "Video / OTT: every title shows its age rating (U, U/A 7+, U/A 13+, U/A 16+, A) as in the IT Rules 2021 Code of Ethics; "
                "parental lock for U/A 13+ and above, age check for A; a grievance officer contact in the app. Subscriptions sold "
                "in the app = store billing.",
    "intermediary": "Users post content: IT Rules (2021, amended 2026) apply: report + block on every post / person, a grievance "
                    "officer, quick takedown on orders, AI-made photos / videos labelled; children's data needs a parent's consent "
                    "(DPDP).",
    "messaging": "Chat: report + block on every chat, no reading the phone's SMS / call log / all contacts (pick a contact or invite "
                 "link instead), media saved only when she taps save.",
    "news_code": "News: source and time on every story, corrections shown, no invented quotes; digital news publishers follow the IT "
                 "Rules 2021 Code of Ethics (grievance officer).",
    "real_money_ban": "Games: free-to-play only. Real-money games, cash prizes, betting, fantasy for money are banned in India (Promotion "
                      "and Regulation of Online Gaming Act 2025); coins / stars can't be bought back or cashed out.",
    "ride_aggregator": "Rides: driver name, photo, vehicle number and ride OTP before the trip, SOS + share-trip always visible, fare "
                       "estimate before booking; running it needs a state aggregator licence (Motor Vehicle Aggregator Guidelines "
                       "2025). Payment by UPI app / cash; never card / UPI PIN fields.",
    "marketplace": "Marketplace: each seller's name, address and licence (FSSAI for food) on its page, grievance officer, "
                   "country of origin / MRP where the law asks (Consumer Protection (E-Commerce) Rules 2020, Legal Metrology).",
    "telemedicine": "Doctor consults: the doctor's registration number on every profile and prescription (NMC Telemedicine Practice "
                    "Guidelines), consent before a video consult, no diagnosis by the app itself, health data is sensitive.",
    "jobs_safety": "Jobs: never charge job seekers a fee, verified employers marked, a 'report job' on every post, salary shown as "
                   "the employer gave it.",
    "property_rera": "Property: RERA registration number on project listings, 'estimate' on EMI numbers, report listing.",
    "payments_licence": "Payments: a UPI / wallet app needs an RBI / NPCI licence or a licensed bank partner; the UPI PIN is typed only "
                        "in the bank's own NPCI screen, never in the app's screens; new-payee warnings.",
    "kids_safe": "If children may use it: no ads that track them, parent's consent for under-18 data (DPDP), no open chat with strangers.",
    "personal_data": "Her own notes / money / health entries stay on the phone or her account; no reading bank SMS (restricted on Play): "
                     "she types it, scans a bill, or imports a statement.",
    "weather_source": "Weather: name the data source and the time it was updated; warnings from IMD shown as IMD's.",
}

# ---------------------------------------------------------------- brands: a reference for the KIND of app, never copied
LIKE: dict[str, list[str]] = {
    "music_streaming": ["spotify", "gaana", "jiosaavn", "jio saavn", "saavn", "wynk", "apple music", "youtube music", "amazon music",
                        "hungama", "soundcloud", "resso"],
    "podcast": ["apple podcasts", "google podcasts", "spotify podcasts"],
    "audiobook": ["pocket fm", "kuku fm", "audible", "storytel"],
    "video_streaming": ["netflix", "hotstar", "jiohotstar", "jio hotstar", "prime video", "amazon prime", "jiocinema", "jio cinema",
                        "zee5", "sonyliv", "sony liv", "mx player", "hoichoi", "voot", "disney"],
    "short_video": ["tiktok", "tik tok", "reels", "youtube shorts", "moj", "josh", "chingari", "roposo", "snapchat spotlight"],
    "social_feed": ["instagram", "insta", "facebook", "pinterest", "sharechat", "koo", "threads", "twitter"],
    "messenger": ["whatsapp", "telegram", "signal", "messenger", "arattai", "hike"],
    "news_reader": ["inshorts", "dailyhunt", "google news", "way2news"],
    "ebook_reader": ["kindle", "google play books", "wattpad", "pratilipi", "kuku"],
    "notes_todo": ["notion", "evernote", "google keep", "todoist", "microsoft to do", "ticktick", "onenote"],
    "habit_tracker": ["habitica", "loop habit"],
    "expense_tracker": ["splitwise", "walnut", "money manager", "axio"],
    "fitness_tracker": ["healthifyme", "fitbit", "strava", "google fit", "cult fit", "cultfit", "nike training"],
    "meditation": ["headspace", "calm app", "insight timer"],
    "recipe_app": ["cookpad", "tasty app", "sanjeev kapoor"],
    "casual_game": ["candy crush", "ludo king", "subway surfers", "kbc", "quiz app like kbc", "temple run", "wordle"],
    "photo_editor": ["picsart", "snapseed", "lightroom", "canva", "vsco", "remini", "capcut"],
    "weather": ["accuweather", "weather channel", "windy"],
    "ride_hailing": ["uber", "ola", "rapido", "blusmart", "namma yatri", "indrive", "in drive"],
    "food_delivery": ["zomato", "swiggy", "eatsure", "magicpin", "ubereats", "uber eats"],
    "quick_commerce": ["blinkit", "zepto", "instamart", "bigbasket", "big basket", "dunzo", "jiomart", "flipkart minutes", "bb now"],
    "marketplace": ["amazon", "flipkart", "meesho", "myntra", "ajio", "nykaa", "snapdeal", "shopsy", "ebay"],
    "classifieds": ["olx", "quikr", "cashify"],
    "travel_booking": ["makemytrip", "make my trip", "goibibo", "redbus", "red bus", "irctc", "ixigo", "cleartrip", "easemytrip", "yatra"],
    "hotel_booking": ["airbnb", "oyo", "booking com", "booking.com", "agoda", "treebo", "fabhotels"],
    "event_tickets": ["bookmyshow", "book my show", "paytm insider", "district app", "ticketmaster"],
    "job_portal": ["naukri", "linkedin", "indeed", "apna", "workindia", "foundit", "internshala"],
    "language_learning": ["duolingo", "babbel", "hello english"],
    "online_learning": ["byjus", "byju", "unacademy", "physics wallah", "physicswallah", "coursera", "udemy", "vedantu", "khan academy"],
    "property_portal": ["99acres", "magicbricks", "housing com", "nobroker", "no broker", "squareyards"],
    "doctor_consult": ["practo", "mfine", "tata 1mg consult", "apollo 24 7", "apollo 247"],
    "services_marketplace": ["urban company", "urbanclap", "housejoy", "justdial"],
    "payments_app": ["paytm", "phonepe", "phone pe", "google pay", "gpay", "bhim", "mobikwik", "cred"],
}
# brands that are also everyday channels / words ("whatsapp se order", "instagram pe bechti hoon", "josh"): they count
# only with a 'like' word next to them ("WhatsApp jaisa", "like Amazon", "Ola ki tarah")
NEEDS_LIKE = {"whatsapp", "instagram", "insta", "facebook", "amazon", "amazon prime", "flipkart", "meesho", "myntra", "ajio", "nykaa",
              "google pay", "gpay", "phonepe", "phone pe", "paytm", "bhim", "cred", "telegram", "signal", "messenger", "threads",
              "twitter", "zomato", "swiggy", "linkedin", "olx", "justdial", "josh", "moj", "kuku", "reels", "koo", "apna", "indeed",
              "hike", "disney", "ola", "district app", "youtube music", "jiomart", "big basket", "bigbasket", "ebay", "irctc",
              "naukri", "practo", "canva", "kbc", "ludo king", "cultfit", "cult fit", "google news", "google fit", "calm app",
              "uber", "storytel", "pinterest", "sharechat", "magicpin", "redbus", "red bus", "oyo", "airbnb", "booking com",
              "booking.com", "agoda"}
LIKE_WORDS = ("jaisa", "jaisi", "jaise", "jesa", "jesi", "like", "clone", "type", "tarah", "similar", "alternative", "copy",
              "version", "जैसा", "जैसी", "जैसे", "सारखा", "सारखी", "सारखे", "सारखं", "प्रमाणे")


def _liked(t: str, brand: str) -> bool:
    toks = t.split()
    bt = brand.split()
    for i in range(len(toks) - len(bt) + 1):
        if toks[i:i + len(bt)] == bt:
            near = toks[max(0, i - 3):i] + toks[i + len(bt):i + len(bt) + 3]
            if any(w in near or (w == "tarah" and "tarah" in near) for w in LIKE_WORDS):
                return True
    return False


# brands of things Hoola won't make (real-money games are banned in India)
REFUSE: dict[str, str] = {w: "real_money" for w in ("dream11", "dream 11", "mpl", "my11circle", "rummycircle", "rummy circle",
                                                     "winzo", "junglee rummy", "pokerbaazi", "a23", "zupee", "teen patti real")}
REFUSE_LINE = ("Real-money games / fantasy for paise India mein band hain (Online Gaming Act 2025). Main free-to-play game ya quiz "
               "app bana sakta hoon: coins / stars ke saath, bina paise ke.")


def _p(label: str, hi: str, *, tabs: list[str], flow: list[str], more: list[str], words: list[str], brief: str,
       modules: list[str], caps: list[str], legal: list[str], styles: list[str], moods: list[str], questions: list[str],
       trust: list[str], money: bool = False, accounts: bool = True, roles: list[str] | None = None, levels: str = "company",
       auth: list[str] | None = None, avoid: list[str] | None = None, core: list[str] | None = None) -> dict[str, Any]:
    screens: list[str] = []
    for s in (["onboarding", "login"] if accounts else ["onboarding"]) + tabs + flow + more:
        if s not in screens:
            screens.append(s)
    return {"label": label, "hi": hi, "accounts": accounts, "money": money, "screens": screens, "tabs": tabs, "flow": flow,
            "words": words, "brief": brief, "product": True, "modules": modules, "roles": roles or ["super_admin", "admin", "staff", "customer"],
            "levels": levels, "caps": caps, "auth": auth or ["phone_otp", "google", "apple", "biometric_unlock"], "styles": styles,
            "legal": legal, "moods": moods, "questions": questions, "trust": trust, "avoid": avoid or [], "core": core or []}


MEDIA = ["aurora_glass", "dark_neon", "mesh_gradient"]
SOCIAL = ["playful_pop", "mesh_gradient", "clean_commerce"]
CALM = ["soft_pastel", "neo_soft", "minimal_mono"]
TOOLS = ["minimal_mono", "neo_soft", "clean_commerce"]
COMMERCE = ["clean_commerce", "bold_blocks", "playful_pop"]
AUDIO_AUTH = ["phone_otp", "email_password", "google", "apple", "biometric_unlock"]

PRODUCTS: dict[str, dict[str, Any]] = {
    "music_streaming": _p("Music streaming app", "gaane sunne ka app",
                          tabs=["home", "search", "library", "profile"], flow=["home", "playlist", "now_playing", "queue"],
                          more=["album", "artist", "browse_genres", "lyrics", "downloads", "plans", "notifications"],
                          words=["music streaming", "music app", "music player", "song app", "songs app", "gaane sunne", "gaana sunne",
                                 "gane sunne", "gaane ka app", "gaano ka app", "songs sunne", "music sunne", "listen to music",
                                 "listening music", "listen music", "music listening", "audio streaming", "playlist app", "mp3 app",
                                 "गाने सुनने", "गाना सुनने", "संगीत", "गाणी ऐकण्या"],
                          avoid=["music class", "music classes", "music academy", "music school", "sikhna", "sikhane", "instrument",
                                 "guitar shop", "music shop", "dj booking", "band booking", "recording studio", "studio booking",
                                 "tuition", "teacher", "lesson", "lessons", "sikhaane", "sangeet vidyalaya"],
                          brief="A music streaming app: home with rails (recently played, made for you, new releases, regional "
                                "languages), search by song / artist / album, a library of playlists and downloads, a full "
                                "now-playing player with seek bar, lyrics and queue, artist and album pages, and a mini player "
                                "above the tab bar on every screen.",
                          modules=["media", "sales"], caps=["push_fcm", "offline_db", "background_sync", "play_billing", "share_sheet",
                                                            "deep_links", "widgets"],
                          legal=["music_licence"], styles=MEDIA, moods=["dark", "bold", "playful"],
                          questions=["App ka naam kya rakhein? (Spotify jaisa naam / logo nahi le sakte, apna naam chahiye)",
                                     "Gaane kahan se aayenge: aapke apne / licensed gaane, ya abhi sirf demo?",
                                     "Free with ads, subscription, ya dono?"],
                          trust=["licensed music", "offline downloads", "regional languages"], auth=AUDIO_AUTH,
                          core=["song", "play", "playlist", "artist", "album", "gaana", "track"]),
    "podcast": _p("Podcast app", "podcast app", tabs=["home", "search", "library", "profile"],
                  flow=["home", "show_page", "now_playing", "queue"], more=["browse_genres", "downloads", "notifications"],
                  words=["podcast", "podcasts", "podcast app", "audio shows", "पॉडकास्ट"], avoid=["podcast studio booking"],
                  brief="A podcast app: follow shows, new episodes first, player with speed and sleep timer, downloads for offline.",
                  modules=["media"], caps=["push_fcm", "offline_db", "background_sync", "share_sheet", "deep_links"],
                  legal=["music_licence"], styles=MEDIA, moods=["dark", "calm"],
                  questions=["App ka naam kya rakhein?", "Shows aapke apne honge ya kai creators ke?"],
                  trust=["new episodes alerts", "offline"], auth=AUDIO_AUTH, core=["episode", "podcast", "show", "listen"]),
    "audiobook": _p("Audiobook / audio stories app", "audio kahani app", tabs=["home", "search", "library", "profile"],
                    flow=["home", "book_detail", "now_playing"], more=["browse_genres", "plans", "downloads", "notifications"],
                    words=["audiobook", "audio book", "audio stories", "audio kahani", "kahani sunne", "story sunne", "audio series"],
                    brief="Audiobooks / audio series: chapters, continue listening, speed control, coins or subscription via store billing.",
                    modules=["media", "sales"], caps=["push_fcm", "offline_db", "play_billing", "background_sync"],
                    legal=["music_licence"], styles=MEDIA, moods=["dark", "warm"],
                    questions=["App ka naam kya rakhein?", "Kahaniyan kis bhasha mein?"], trust=["new episodes daily"],
                    core=["chapter", "listen", "story", "episode"]),
    "video_streaming": _p("Video streaming (OTT) app", "video / OTT app", tabs=["home", "search", "watchlist", "downloads", "profile"],
                          flow=["profiles_picker", "home", "title_detail", "video_player"],
                          more=["browse_genres", "parental_controls", "plans", "notifications"],
                          words=["ott", "ott app", "video streaming", "movie app", "movies app", "web series", "series app",
                                 "film dekhne", "movie dekhne", "picture dekhne", "video dekhne ka app", "shows dekhne", "streaming app",
                                 "फिल्म देखने", "वेब सीरीज"],
                          avoid=["cable", "set top box", "iptv", "dth", "video editing", "videographer", "shooting"],
                          brief="An OTT app: viewer profiles incl. kids, home rails (continue watching, trending, languages), title "
                                "pages with age rating, episodes and trailer, a full player with subtitles / quality / skip intro, "
                                "my list, downloads and parental controls.",
                          modules=["media", "sales"], caps=["push_fcm", "offline_db", "play_billing", "background_sync", "deep_links",
                                                            "share_sheet"],
                          legal=["ott_code", "kids_safe"], styles=["dark_neon", "luxury_noir", "aurora_glass"], moods=["dark", "bold"],
                          questions=["App ka naam kya rakhein? (kisi OTT ka naam / logo nahi)", "Videos kiske honge: aapke apne / licensed?",
                                     "Subscription, rent per movie, ya free with ads?"],
                          trust=["age ratings", "parental lock", "downloads"], core=["watch", "play", "episode", "season", "movie", "series"]),
    "short_video": _p("Short video app", "chhote video (reels) app", tabs=["reel_feed", "explore", "create_post", "chat_list", "user_profile"],
                      flow=["reel_feed", "comments", "user_profile"],
                      more=["followers", "report_content", "chat_thread", "notifications", "search"],
                      words=["short video", "short videos", "reels app", "reel app", "video sharing", "chhote video", "vertical video",
                             "शॉर्ट वीडियो", "रील"],
                      brief="A short-video app: full-screen vertical feed, like / comment / share / follow, create with camera + "
                            "music + text, profiles, chats, and report / block everywhere.",
                      modules=["social", "media", "comms"], caps=["camera", "microphone", "photo_picker", "push_fcm", "share_sheet",
                                                                   "deep_links", "background_sync"],
                      legal=["intermediary", "kids_safe"], styles=SOCIAL + ["dark_neon"], moods=["bold", "playful", "dark"],
                      questions=["App ka naam kya rakhein?", "Kaun video daalega: sab log, ya sirf chune hue creators?"],
                      trust=["report + block", "AI label"], core=["like", "comment", "share", "follow", "video", "reel"]),
    "social_feed": _p("Social media app", "social media app", tabs=["feed", "explore", "create_post", "notifications", "user_profile"],
                      flow=["feed", "post_detail", "comments", "user_profile"],
                      more=["stories", "followers", "chat_list", "chat_thread", "report_content", "search"],
                      words=["social media", "social app", "social network", "photo sharing", "community feed", "posts app",
                             "followers app", "सोशल मीडिया"],
                      avoid=["social media marketing", "social media manager", "smm"],
                      brief="A social app: stories, a feed of posts from people she follows, likes / comments / shares, explore, "
                            "creating posts with photos and captions, public profiles, chats, and report / block on everything.",
                      modules=["social", "comms"], caps=["camera", "photo_picker", "push_fcm", "share_sheet", "deep_links", "background_sync"],
                      legal=["intermediary", "kids_safe"], styles=SOCIAL, moods=["playful", "bold"],
                      questions=["App ka naam kya rakhein?", "Kis ke liye: sab ke liye, ya ek samuh (college, society, community)?"],
                      trust=["report + block", "private accounts"], core=["post", "like", "comment", "follow", "story"]),
    "messenger": _p("Chat / messaging app", "chat app", tabs=["chat_list", "stories", "new_chat", "profile"],
                    flow=["chat_list", "chat_thread", "media_viewer"], more=["group_info", "report_content", "search", "notifications"],
                    words=["chat app", "chatting app", "messaging app", "messenger app", "baat karne ka app", "message app",
                           "group chat app", "चैट ऐप"],
                    brief="A chat app: chats list, one-to-one and group chats with photos, voice notes and reactions, status "
                          "stories, new chat / group, group info, report / block.",
                    modules=["comms", "social"], caps=["camera", "microphone", "voice_notes", "photo_picker", "contacts_pick",
                                                       "push_fcm", "share_sheet", "background_sync"],
                    legal=["messaging", "intermediary"], styles=["clean_commerce", "neo_soft", "minimal_mono"], moods=["calm", "clean"],
                    questions=["App ka naam kya rakhein?", "Kis ke liye: sab ke liye, ya ek company / samuh ke andar?"],
                    trust=["report + block", "no contact upload"], core=["chat", "message", "send", "group"]),
    "news_reader": _p("News app", "khabar app", tabs=["home", "topics", "bookmarks", "profile"], flow=["home", "article"],
                      more=["search", "notifications", "video_player"],
                      words=["news app", "khabar", "khabron", "samachar", "news reader", "headlines", "समाचार", "ख़बर", "बातम्या"],
                      avoid=["newspaper agency", "newspaper vendor", "akhbar wala"],
                      brief="A news app: top stories and local news by city and language, short cards and full articles, topics to "
                            "follow, saved stories, breaking-news alerts.",
                      modules=["media", "social"], caps=["push_fcm", "share_sheet", "offline_db", "deep_links"],
                      legal=["news_code"], styles=["editorial_image", "minimal_mono", "clean_commerce"], moods=["clean", "bold"],
                      questions=["App ka naam kya rakhein?", "Khabrein kaun likhega: aapki team, ya kai sources?", "Kaun si bhashayein?"],
                      trust=["source on every story", "corrections"], core=["news", "story", "headline", "read"]),
    "ebook_reader": _p("E-book / reading app", "kitaab padhne ka app", tabs=["home", "library", "search", "profile"],
                       flow=["home", "book_detail", "reader"], more=["bookmarks", "plans", "downloads", "browse_genres"],
                       words=["ebook", "e book", "e-book", "book reading", "kitaab padhne", "novel app", "reading app", "kahani padhne",
                              "किताब पढ़ने"],
                       avoid=["book shop", "book store", "stationery"],
                       brief="A reading app: library, store / free shelf, a clean reader with font / theme / progress, highlights.",
                       modules=["media", "sales"], caps=["offline_db", "play_billing", "push_fcm"], legal=["music_licence"],
                       styles=["paper_craft", "editorial_image", "minimal_mono"], moods=["calm", "warm"],
                       questions=["App ka naam kya rakhein?", "Kitaabein kiski: aapki apni / licensed?"], trust=["offline reading"],
                       core=["book", "read", "chapter", "page"]),
    "notes_todo": _p("Notes & to-do app", "notes aur kaam ki list", tabs=["note_list", "today_tasks", "search", "profile"],
                     flow=["note_list", "note_editor", "today_tasks"], more=["notifications"],
                     words=["notes app", "note app", "todo", "to do", "to-do", "task list", "checklist app", "reminder app",
                            "notes likhne", "kaam ki list", "नोट्स"],
                     brief="A notes + to-do app: colourful notes grid, editor with checklist / photo / reminder, today's tasks, search.",
                     modules=["personal"], caps=["local_reminders", "offline_db", "background_sync", "speech_to_text", "widgets"],
                     legal=["personal_data"], styles=TOOLS, moods=["calm", "clean"],
                     questions=["App ka naam kya rakhein?", "Phone par hi rahe, ya login karke sab phones par sync?"],
                     trust=["works offline", "private"], core=["note", "task", "today", "list"]),
    "habit_tracker": _p("Habit tracker", "aadat tracker", tabs=["habit_today", "stats_chart", "habit_edit", "profile"],
                        flow=["habit_today", "habit_edit", "stats_chart"], more=["notifications"],
                        words=["habit tracker", "habit app", "aadat", "daily routine app", "streak app", "आदत"],
                        brief="A habit tracker: today's habits with big ticks and streaks, create a habit with days and a reminder, "
                              "weekly / monthly stats.",
                        modules=["personal"], caps=["local_reminders", "offline_db", "widgets"], legal=["personal_data"],
                        styles=CALM, moods=["calm", "playful"], questions=["App ka naam kya rakhein?"],
                        trust=["private", "reminders"], core=["habit", "streak", "today", "done"]),
    "expense_tracker": _p("Expense tracker", "kharcha hisaab app", tabs=["expense_home", "stats_chart", "split_groups", "profile"],
                          flow=["expense_home", "expense_add", "stats_chart"], more=["budget_view", "notifications"],
                          words=["expense tracker", "expense app", "kharcha", "kharche ka hisaab", "budget app", "money manager",
                                 "split bills", "bill split", "खर्चा", "हिसाब"],
                          avoid=["khata book", "udhaar", "dukaan ka hisaab", "shop accounts", "billing software"],
                          brief="A personal expense tracker: add spending fast, categories, budgets, monthly charts, shared groups "
                                "with friends and settle-up links to their UPI ID.",
                          modules=["personal"], caps=["offline_db", "camera", "ocr", "upi_intent", "local_reminders", "widgets"],
                          legal=["personal_data"], styles=TOOLS, moods=["clean", "calm"],
                          questions=["App ka naam kya rakhein?", "Sirf apna kharcha, ya doston ke saath baantna bhi?"],
                          trust=["no SMS reading", "private"], core=["expense", "spent", "budget", "amount"]),
    "fitness_tracker": _p("Fitness tracker", "fitness app", tabs=["activity_home", "workouts", "stats_chart", "profile"],
                          flow=["activity_home", "workouts", "workout_player", "stats_chart"], more=["plans", "notifications"],
                          words=["fitness tracker", "fitness app", "workout app", "step counter", "steps app", "calorie counter",
                                 "exercise app", "home workout", "फिटनेस"],
                          avoid=["gym membership", "gym ki app", "mera gym", "gym owner", "fitness studio", "yoga studio"],
                          brief="A fitness app: today's steps / minutes / calories rings, workouts by type and level, a guided "
                                "workout player with timer, weekly stats, streaks.",
                          modules=["personal", "media"], caps=["activity", "health_connect", "local_reminders", "offline_db", "play_billing"],
                          legal=["personal_data"], styles=["bold_blocks", "dark_neon", "fresh_organic"], moods=["bold", "fresh"],
                          questions=["App ka naam kya rakhein?", "Workout videos aapke apne honge?"],
                          trust=["not medical advice", "private"], core=["workout", "steps", "minutes", "calories"]),
    "meditation": _p("Meditation & sleep app", "dhyan app", tabs=["home", "browse_genres", "stats_chart", "profile"],
                     flow=["home", "session_player"], more=["plans", "downloads", "notifications"],
                     words=["meditation", "dhyan", "sleep app", "breathing app", "mindfulness", "pranayam", "ध्यान"],
                     avoid=["meditation centre", "yoga class", "yoga studio"],
                     brief="A meditation app: daily calm session, breathing animation, sleep sounds, streaks.",
                     modules=["media", "personal"], caps=["offline_db", "local_reminders", "play_billing", "background_sync"],
                     legal=["personal_data"], styles=CALM, moods=["calm"], questions=["App ka naam kya rakhein?"],
                     trust=["not medical advice"], core=["breathe", "calm", "minutes", "session"]),
    "recipe_app": _p("Recipe app", "recipe app", tabs=["home", "search", "bookmarks", "profile"],
                     flow=["home", "recipe_detail", "cook_mode"], more=["browse_genres", "shopping_list"],
                     words=["recipe app", "recipes app", "khana banane", "cooking app", "recipe", "रेसिपी"],
                     avoid=["restaurant", "cloud kitchen", "tiffin", "catering", "food delivery"],
                     brief="A recipe app: recipes by cuisine / time / veg, step-by-step cook mode with timers, saved recipes, a "
                           "shopping list from ingredients.",
                     modules=["media", "personal"], caps=["offline_db", "share_sheet", "speech_to_text"], legal=[],
                     styles=["fresh_organic", "editorial_image", "desi_festive"], moods=["warm", "food"],
                     questions=["App ka naam kya rakhein?", "Recipes aapki apni honge?"], trust=["veg marks"],
                     core=["recipe", "ingredients", "steps", "minutes"]),
    "casual_game": _p("Game / quiz app", "game / quiz app", tabs=["game_home", "level_map", "leaderboard", "profile"],
                      flow=["game_home", "level_map", "game_play", "game_result"], more=["rewards", "notifications"],
                      words=["game app", "game banao", "quiz app", "quiz game", "puzzle game", "trivia", "ludo", "word game",
                             "khel", "गेम", "क्विज़"],
                      avoid=["real money", "paise jeeto", "betting", "satta", "rummy", "fantasy", "casino"],
                      brief="A free-to-play game / quiz: play button and daily challenge, a level path with stars, the game board "
                            "with timer and score, result with stars, weekly leaderboard (points only).",
                      modules=["personal", "social"], caps=["push_fcm", "offline_db", "share_sheet"], legal=["real_money_ban", "kids_safe"],
                      styles=["playful_pop", "dark_neon", "bold_blocks"], moods=["playful", "bold"],
                      questions=["Game ka naam kya rakhein?", "Kis cheez ka quiz / game (GK, padhai, shabd, puzzle)?"],
                      trust=["free to play", "no real money"], core=["play", "level", "score", "stars"]),
    "photo_editor": _p("Photo editor app", "photo editor", tabs=["home", "templates", "gallery", "profile"],
                       flow=["home", "editor_canvas", "filters_panel", "export_share"], more=["plans"],
                       words=["photo editor", "photo editing", "image editor", "photo edit", "collage maker", "filters app",
                              "फोटो एडिटर"],
                       avoid=["photo studio", "photographer", "studio booking"],
                       brief="A photo editor: pick a photo, crop / adjust / filters / text / stickers, templates for festivals and "
                             "stories, save and share.",
                       modules=["media"], caps=["photo_picker", "camera", "share_sheet", "play_billing"], legal=["intermediary"],
                       styles=["dark_neon", "mesh_gradient", "playful_pop"], moods=["bold", "playful"],
                       questions=["App ka naam kya rakhein?"], accounts=False, trust=["no watermark lies"],
                       core=["edit", "filter", "crop", "save"]),
    "weather": _p("Weather app", "mausam app", tabs=["forecast", "radar_map", "city_list"], flow=["forecast", "day_detail"],
                  more=[], words=["weather app", "mausam", "weather forecast", "baarish ka app", "मौसम", "हवामान"],
                  brief="A weather app: now / hourly / 7 days, rain chance, AQI, rain map, saved cities, alerts.",
                  modules=["personal"], caps=["location_foreground", "maps", "push_fcm", "widgets"], legal=["weather_source"],
                  styles=["aurora_glass", "mesh_gradient", "minimal_mono"], moods=["calm", "fresh"],
                  questions=["App ka naam kya rakhein?"], accounts=False, trust=["source + time"],
                  core=["temperature", "rain", "forecast", "weather"]),
    "ride_hailing": _p("Ride booking app", "ride / cab app", tabs=["ride_home", "ride_history", "support", "profile"],
                       flow=["ride_home", "ride_options", "ride_track", "ride_rating"], more=["notifications", "payment"],
                       words=["ride app", "ride booking", "cab app", "cab booking", "taxi app", "bike taxi", "auto booking",
                              "ride hailing", "कैब", "टैक्सी"],
                       avoid=["mera taxi stand", "travel agency", "tour package", "car rental shop", "driving school"],
                       brief="A ride app: map with pickup, 'where to', options with fare and time (bike / auto / cab), driver "
                             "on the way with vehicle number and ride OTP, SOS and share trip, rating and receipt.",
                       modules=["market", "logistics", "sales"], caps=["location_foreground", "maps", "push_fcm", "upi_intent",
                                                                        "call_dialer", "share_sheet"],
                       legal=["ride_aggregator"], styles=["bold_blocks", "clean_commerce", "dark_neon"], moods=["bold", "clean"],
                       questions=["App ka naam kya rakhein?", "Kaun si gaadiyan: bike, auto, cab?", "Kis shehar mein?"],
                       trust=["verified drivers", "SOS"], money=True, roles=["super_admin", "admin", "dispatcher", "driver", "customer"],
                       levels="logistics", core=["ride", "pickup", "driver", "fare"]),
    "food_delivery": _p("Food delivery app (many restaurants)", "khana delivery app", tabs=["home", "search", "orders", "profile"],
                        flow=["home", "store_list", "store_page", "cart", "checkout", "order_track"],
                        more=["dish_detail", "offers", "payment", "order_success", "support", "notifications"],
                        words=["food delivery app", "food delivery platform", "food ordering platform", "multi restaurant",
                               "many restaurants", "sabhi restaurants", "restaurant aggregator", "food marketplace", "khana mangwane ka app"],
                        avoid=["mera restaurant", "my restaurant", "hamara restaurant", "mere restaurant", "meri hotel", "mera hotel",
                               "mera dhaba", "mera cafe", "meri bakery", "restaurant ki app", "restaurant ka app", "cafe ki app"],
                        brief="A food delivery marketplace: many restaurants near her with rating, time, offers and veg filter, "
                              "each restaurant's menu with FSSAI number, cart, checkout by UPI app / cash, live order tracking.",
                        modules=["market", "sales", "logistics"], caps=["location_foreground", "maps", "push_fcm", "upi_intent", "share_sheet"],
                        legal=["marketplace", "fssai"], styles=COMMERCE, moods=["food", "bold", "warm"],
                        questions=["App ka naam kya rakhein?", "Kis shehar / area mein?", "Delivery kaun karega: apne riders ya restaurant?"],
                        trust=["FSSAI on every restaurant", "live tracking"], money=True,
                        roles=["super_admin", "admin", "vendor", "driver", "customer"], levels="logistics",
                        core=["restaurant", "order", "delivery", "menu"]),
    "quick_commerce": _p("Quick delivery app (10-minute groceries)", "10 minute delivery app", tabs=["home", "categories", "orders", "profile"],
                         flow=["home", "product_list", "product_detail", "cart", "checkout", "order_track"],
                         more=["search", "offers", "payment", "order_success", "support"],
                         words=["quick commerce", "10 minute delivery", "10 min delivery", "instant delivery app", "dark store",
                                "grocery delivery platform", "minutes mein delivery"],
                         avoid=["meri kirana", "mera kirana", "meri dukaan", "my shop"],
                         brief="A quick-delivery app: delivery time on top, categories, products with MRP, cart, UPI checkout, "
                               "live rider tracking.",
                         modules=["sales", "inventory", "logistics", "market"], caps=["location_foreground", "maps", "push_fcm",
                                                                                     "upi_intent", "barcode"],
                         legal=["marketplace", "legal_metrology", "fssai"], styles=COMMERCE, moods=["fresh", "bold"],
                         questions=["App ka naam kya rakhein?", "Kis shehar / area mein?"], trust=["MRP shown", "live tracking"],
                         money=True, roles=["super_admin", "admin", "staff", "driver", "customer"], levels="logistics",
                         core=["delivery", "cart", "minutes", "order"]),
    "marketplace": _p("Online shopping marketplace", "online shopping app (kai sellers)", tabs=["home", "categories", "cart", "orders", "profile"],
                      flow=["home", "product_list", "product_detail", "cart", "checkout", "order_success"],
                      more=["search", "wishlist", "offers", "store_page", "payment", "order_track", "support", "notifications"],
                      words=["shopping app", "online shopping", "e commerce app", "ecommerce app", "marketplace app", "multi vendor",
                             "multivendor", "many sellers", "online bazaar", "शॉपिंग ऐप"],
                      avoid=["meri dukaan", "mera shop", "my shop", "my store", "meri shop", "mera showroom"],
                      brief="A multi-seller shopping app: search, categories, product pages with MRP / seller / returns, wishlist, "
                            "cart, UPI checkout, order tracking, each seller's own store page.",
                      modules=["sales", "inventory", "logistics", "market", "crm"], caps=["push_fcm", "upi_intent", "share_sheet",
                                                                                         "deep_links", "camera"],
                      legal=["marketplace", "legal_metrology"], styles=COMMERCE, moods=["bold", "clean"],
                      questions=["App ka naam kya rakhein?", "Kya bikega: kapde, electronics, sab kuch?", "Sellers kaun honge?"],
                      trust=["seller details", "easy returns"], money=True,
                      roles=["super_admin", "admin", "vendor", "customer"], core=["cart", "price", "seller", "order"]),
    "classifieds": _p("Buy & sell (classifieds) app", "purana saamaan bechne ka app", tabs=["home", "chat_list", "post_ad", "my_ads", "profile"],
                      flow=["home", "listing_detail", "chat_thread"], more=["search", "categories", "report_content", "notifications"],
                      words=["classifieds", "buy and sell", "buy sell", "second hand", "purana saamaan", "used items", "old items sell",
                             "olx jaisa"],
                      brief="A buy & sell app: nearby listings by category, ad page with photos / price / seller, chat with the "
                            "seller, post an ad, my ads, report.",
                      modules=["market", "comms", "social"], caps=["camera", "photo_picker", "location_foreground", "push_fcm", "share_sheet"],
                      legal=["intermediary"], styles=COMMERCE, moods=["bold", "clean"],
                      questions=["App ka naam kya rakhein?", "Kis shehar / kis cheez ke liye (sab kuch, gaadiyan, phones)?"],
                      trust=["safety tips", "report ad"], core=["price", "sell", "ad", "chat"]),
    "travel_booking": _p("Travel booking app", "ticket booking app (bus / train / flight)", tabs=["trip_search", "my_trips", "offers", "profile"],
                         flow=["trip_search", "trip_results", "seat_select", "traveller_details", "payment", "ticket_view"],
                         more=["support", "notifications", "order_success"],
                         words=["ticket booking app", "bus booking", "bus ticket", "train ticket", "flight booking", "flight ticket",
                                "travel booking app", "yatra booking"],
                         avoid=["meri travel agency", "mera tour", "tour package", "travels ka office"],
                         brief="A travel booking app: search from / to / date, results with time / duration / price, seat map, "
                               "traveller details (no card fields), payment, ticket with QR / PNR, my trips.",
                         modules=["sales", "events", "market"], caps=["push_fcm", "upi_intent", "calendar", "share_sheet", "offline_db"],
                         legal=["marketplace"], styles=["clean_commerce", "aurora_glass", "bold_blocks"], moods=["fresh", "clean"],
                         questions=["App ka naam kya rakhein?", "Kya book hoga: bus, train, flight, sab?"], trust=["clear refund rules"],
                         money=True, core=["ticket", "seat", "date", "from"]),
    "hotel_booking": _p("Hotel / stay booking app", "hotel booking app", tabs=["trip_search", "wishlist", "my_trips", "profile"],
                        flow=["trip_search", "trip_results", "stay_detail", "traveller_details", "payment", "ticket_view"],
                        more=["map_search", "support", "notifications"],
                        words=["hotel booking app", "stay booking", "homestay booking", "room booking app", "holiday stays"],
                        avoid=["mera hotel", "meri hotel", "my hotel", "hamara hotel", "hotel ki app", "resort ki app"],
                        brief="A stays app: search by place and dates, stays with price per night, photos / amenities / rules / map, "
                              "booking and the booking card.",
                        modules=["hospitality", "sales", "market"], caps=["maps", "location_foreground", "push_fcm", "upi_intent", "calendar"],
                        legal=["marketplace"], styles=["editorial_image", "luxury_noir", "aurora_glass"], moods=["warm", "luxury"],
                        questions=["App ka naam kya rakhein?", "Kis shehar / jagah ke stays?"], trust=["clear cancellation"],
                        money=True, core=["night", "stay", "check-in", "book"]),
    "event_tickets": _p("Event & movie tickets app", "event ticket app", tabs=["home", "search", "my_bookings", "profile"],
                        flow=["home", "event_detail", "seat_select", "payment", "pass"], more=["events", "notifications", "order_success"],
                        words=["event tickets app", "movie tickets", "show tickets", "concert tickets", "ticket booking platform"],
                        avoid=["mera event", "meri shaadi", "event management company"],
                        brief="A tickets app: events / movies near her, event page, seat map, payment, the pass with QR.",
                        modules=["events", "sales"], caps=["push_fcm", "upi_intent", "barcode", "calendar", "location_foreground"],
                        legal=["marketplace"], styles=["dark_neon", "playful_pop", "bold_blocks"], moods=["bold", "festive"],
                        questions=["App ka naam kya rakhein?", "Kis shehar ke events?"], trust=["QR pass"], money=True,
                        core=["ticket", "seat", "show", "event"]),
    "job_portal": _p("Job portal app", "naukri app", tabs=["job_list", "search", "applications", "profile"],
                     flow=["job_list", "job_detail", "resume_builder", "applications"], more=["notifications", "chat_list"],
                     words=["job portal", "job app", "naukri app", "jobs app", "job search app", "rozgar", "recruitment app",
                            "hiring app", "नौकरी"],
                     avoid=["placement agency office", "mera staffing"],
                     brief="A jobs app: job cards with salary and place, job page, simple resume builder, apply, application status.",
                     modules=["market", "comms"], caps=["push_fcm", "files_saf", "share_sheet", "location_foreground"],
                     legal=["jobs_safety", "hiring"], styles=["clean_commerce", "minimal_mono", "bold_blocks"], moods=["clean", "trust"],
                     questions=["App ka naam kya rakhein?", "Kis tarah ki naukriyan (blue collar, office, sab)?"],
                     trust=["no fee for job seekers", "verified employers"], core=["job", "salary", "apply"]),
    "language_learning": _p("Language learning app", "bhasha seekhne ka app", tabs=["learn_path", "quiz", "leaderboard", "profile"],
                            flow=["learn_path", "lesson", "quiz", "game_result"], more=["plans", "rewards", "notifications"],
                            words=["language learning", "english speaking app", "english sikhne", "bhasha sikhne", "learn english",
                                   "spoken english app", "भाषा सीखने"],
                            avoid=["spoken english classes", "english coaching", "meri coaching", "mera institute"],
                            brief="A language app: a lesson path with units, short lessons with audio, quizzes, streaks and XP, "
                                  "weekly leaderboard.",
                            modules=["education", "personal"], caps=["microphone", "speech_to_text", "push_fcm", "local_reminders",
                                                                     "offline_db", "play_billing"],
                            legal=["edu", "kids_safe"], styles=["playful_pop", "fresh_organic", "bold_blocks"], moods=["playful", "fresh"],
                            questions=["App ka naam kya rakhein?", "Kaun si bhasha kis bhasha se?"], trust=["streaks"],
                            core=["lesson", "streak", "xp", "learn"]),
    "online_learning": _p("Online learning platform", "online padhai platform", tabs=["home", "search", "courses", "profile"],
                          flow=["home", "course_detail", "lesson", "quiz"], more=["plans", "downloads", "notifications"],
                          words=["online learning platform", "e learning platform", "elearning app", "course platform",
                                 "online courses app", "edtech app", "mooc"],
                          avoid=["meri coaching", "mera institute", "meri classes", "tuition"],
                          brief="A learning platform: courses from many teachers, course pages, video lessons, quizzes, progress.",
                          modules=["education", "media", "sales"], caps=["offline_db", "play_billing", "push_fcm", "background_sync"],
                          legal=["edu"], styles=["clean_commerce", "fresh_organic", "aurora_glass"], moods=["fresh", "trust"],
                          questions=["App ka naam kya rakhein?", "Kis cheez ke courses?"], trust=["progress tracking"],
                          core=["course", "lesson", "learn", "progress"]),
    "property_portal": _p("Property portal app", "property dhoondhne ka app", tabs=["home", "map_search", "wishlist", "profile"],
                          flow=["home", "property_list", "property_detail", "enquiry"], more=["search", "post_ad", "notifications"],
                          words=["property portal", "property app", "real estate portal", "flat dhoondhne", "ghar dhoondhne",
                                 "rent app", "property listing app", "प्रॉपर्टी"],
                          avoid=["mera project", "builder ka project", "meri agency", "mera office"],
                          brief="A property app: buy / rent listings with price, BHK, area and RERA number, map search, "
                                "property pages, contact owner / agent.",
                          modules=["crm", "market", "gis"], caps=["maps", "location_foreground", "push_fcm", "call_dialer", "share_sheet"],
                          legal=["property_rera", "rera"], styles=["editorial_image", "clean_commerce", "luxury_noir"],
                          moods=["trust", "luxury"], questions=["App ka naam kya rakhein?", "Kis shehar ki property?"],
                          trust=["RERA numbers", "verified listings"], core=["bhk", "price", "property", "rent"]),
    "doctor_consult": _p("Doctor consultation platform", "doctor consult app", tabs=["home", "my_bookings", "support", "profile"],
                         flow=["home", "doctor_list", "slot_picker", "booking_confirm", "consult_room", "prescription"],
                         more=["payment", "notifications"],
                         words=["doctor consultation app", "online doctor", "teleconsultation", "telemedicine app", "video consult",
                                "doctor booking platform"],
                         avoid=["mera clinic", "meri clinic", "my clinic", "mera hospital", "clinic ki app", "hospital ki app"],
                         brief="A consult platform: doctors by speciality with registration number, slot booking, video consult "
                               "room, prescription with the doctor's details.",
                         modules=["health", "sales", "comms"], caps=["camera", "microphone", "push_fcm", "upi_intent", "screen_secure",
                                                                     "keystore"],
                         legal=["telemedicine", "nmc"], styles=["trust_clinical", "neo_soft", "clean_commerce"], moods=["trust", "calm"],
                         questions=["App ka naam kya rakhein?", "Doctors kaun honge (aapke panel ke)?"],
                         trust=["registered doctors", "private"], money=True,
                         roles=["super_admin", "admin", "doctor", "front_desk", "customer"], levels="clinic",
                         core=["doctor", "consult", "slot", "prescription"]),
    "services_marketplace": _p("Home services marketplace", "ghar ki seva ka app (kai professionals)",
                               tabs=["home", "my_bookings", "support", "profile"],
                               flow=["home", "services", "service_detail", "slot_picker", "booking_confirm"],
                               more=["payment", "notifications", "order_track"],
                               words=["home services app", "services marketplace", "urban company jaisa", "plumber electrician app",
                                      "service booking platform"],
                               avoid=["meri service", "mera kaam", "main plumber", "main electrician"],
                               brief="A services marketplace: services by category, verified professionals, price list, slot booking, "
                                     "professional on the way, rating.",
                               modules=["service", "market", "sales"], caps=["location_foreground", "maps", "push_fcm", "upi_intent",
                                                                             "call_dialer"],
                               legal=["marketplace"], styles=COMMERCE, moods=["clean", "trust"],
                               questions=["App ka naam kya rakhein?", "Kis shehar mein, kaun si sevayein?"],
                               trust=["verified professionals"], money=True,
                               roles=["super_admin", "admin", "field", "customer"], levels="service",
                               core=["service", "book", "slot", "professional"]),
    "payments_app": _p("Payments / UPI app", "payment app", tabs=["wallet_home", "scan_pay", "txn_history", "profile"],
                       flow=["wallet_home", "scan_pay", "txn_history"], more=["notifications", "support"],
                       words=["payment app", "payments app", "upi app", "wallet app", "money transfer app", "scan and pay app"],
                       avoid=["payment collect", "upi qr for my shop", "meri dukaan"],
                       brief="A payments app design: scan & pay, pay contacts, history with status; the UPI PIN is typed only in "
                             "the bank's own NPCI screen; running it needs an RBI / NPCI licence or a licensed bank partner.",
                       modules=["finance", "sales"], caps=["barcode", "camera", "biometrics", "screen_secure", "keystore", "push_fcm",
                                                           "app_integrity"],
                       legal=["payments_licence"], styles=["trust_clinical", "clean_commerce", "neo_soft"], moods=["trust", "clean"],
                       questions=["App ka naam kya rakhein?", "Kis bank / licensed partner ke saath chalegi?"],
                       trust=["new-payee warnings"], money=True, core=["pay", "scan", "upi", "history"]),
}

# rule keys used by products: business ones already live in taxonomy.STORE_RULES
_SHARED_RULES = {"fssai", "legal_metrology", "hiring", "rera", "nmc", "edu"}


def field_id(pid: str) -> str:
    return f"app_{pid}"


def pid_of(field: str) -> str:
    return field[4:] if field.startswith("app_") and field[4:] in PRODUCTS else ""


def fields() -> dict[str, dict[str, Any]]:
    """Pseudo business types so the brief / plan / build code works unchanged ('app_music_streaming')."""
    out = {}
    for pid, p in PRODUCTS.items():
        out[field_id(pid)] = {"id": field_id(pid), "en": p["label"], "aliases": p["words"][:8], "hi": p["hi"], "mr": p["hi"],
                              "industry": "product_app", "goal": pid, "cta": "", "legal": list(p["legal"]), "styles": p["styles"],
                              "product": pid}
    return out


def _norm(s: str) -> str:
    s = (s or "").lower().replace(".", " ").replace("-", " ")
    s = re.sub(r"[^\wऀ-ॿ\s]", " ", s)
    return " " + re.sub(r"\s+", " ", s).strip() + " "


def refused(text: str) -> str:
    t = _norm(text)
    return REFUSE_LINE if any(f" {_norm(w).strip()} " in t for w in REFUSE) else ""


def match(text: str) -> dict[str, Any]:
    """Her words -> the product app she means, or {} when she means a business's app.
    {id, label, score, brand (the reference she named, '' if none), why}"""
    t = _norm(text)
    best: dict[str, Any] = {}
    for pid, p in PRODUCTS.items():
        brand = next((b for b in sorted(LIKE.get(pid, []), key=len, reverse=True)
                      if f" {_norm(b).strip()} " in t and (b not in NEEDS_LIKE or _liked(t, _norm(b).strip()))), "")
        score = 3.0 if brand else 0.0
        hits = []
        for w in p["words"]:
            nw = _norm(w).strip()
            if nw and f" {nw} " in t:
                hits.append(w)
                score += len(nw.split())
        if not brand and any(f" {_norm(a).strip()} " in t for a in p["avoid"]):
            continue
        if hits and not brand and score < 2 and any(f" {w} " in t for w in ("app", "apps", "application", "ऐप", "एप")):
            score += 1          # "todo app", "khabar app": one clear word + the word app
        if score >= 2 and (not best or score > best["score"]):
            best = {"id": pid, "label": p["label"], "score": score, "brand": brand, "why": hits[:4]}
    return best


def check() -> list[str]:
    from . import taxonomy as T
    problems: list[str] = []
    for pid, p in PRODUCTS.items():
        for s in p["screens"]:
            if s not in T.SCREENS:
                problems.append(f"product {pid}: unknown screen {s}")
        for t in p["tabs"]:
            if t not in p["screens"]:
                problems.append(f"product {pid}: tab {t}")
        if not 3 <= len(p["tabs"]) <= 5:
            problems.append(f"product {pid}: {len(p['tabs'])} tabs")
        for k in p["legal"]:
            if k not in PRODUCT_RULES and k not in _SHARED_RULES:
                problems.append(f"product {pid}: rule {k}")
        for st in p["styles"]:
            if st not in T.STYLES:
                problems.append(f"product {pid}: style {st}")
        if pid not in LIKE:
            problems.append(f"product {pid}: no brand list")
        if pid not in KEPT:
            problems.append(f"product {pid}: no privacy 'what we keep' lines")
        if pid in PRIMARY and PRIMARY[pid][0] not in p["screens"]:
            problems.append(f"product {pid}: main action {PRIMARY[pid][0]} not a screen")
    return problems


# ---------------------------------------------------------------- privacy page ("what we keep") + the main floating action
_K_MEDIA = ["name and phone / email (login)", "what you play, save and download, to continue where you left off",
            "your subscription status from the store (never card details)"]
_K_SOCIAL = ["name, phone / email and profile photo", "what you post, like, comment and report", "people you follow and block"]
_K_PERSONAL = ["what you write or enter, kept on your phone and (only if you log in) in your account", "reminder times you set"]
_K_MARKET = ["name and phone number (login, updates)", "address / location only while you book or order",
             "your orders / bookings and receipts"]
KEPT: dict[str, list[str]] = {
    **{p: _K_MEDIA for p in ("music_streaming", "podcast", "audiobook", "video_streaming", "ebook_reader", "meditation",
                             "news_reader", "online_learning", "language_learning")},
    **{p: _K_SOCIAL for p in ("short_video", "social_feed", "messenger", "classifieds")},
    **{p: _K_PERSONAL for p in ("notes_todo", "habit_tracker", "expense_tracker", "fitness_tracker", "recipe_app", "casual_game",
                                "photo_editor", "weather")},
    **{p: _K_MARKET for p in ("ride_hailing", "food_delivery", "quick_commerce", "marketplace", "travel_booking", "hotel_booking",
                              "event_tickets", "property_portal", "services_marketplace")},
    "job_portal": ["name, phone / email and the resume you upload", "jobs you apply to and their status"],
    "doctor_consult": ["name, phone number and age", "your bookings, consult notes and prescriptions (kept private)"],
    "payments_app": ["name, phone number and a masked bank account", "your payment history (the UPI PIN is never seen or kept)"],
}
PRIMARY: dict[str, tuple[str, str]] = {
    "music_streaming": ("now_playing", "play"), "podcast": ("now_playing", "play"), "audiobook": ("now_playing", "play"),
    "video_streaming": ("video_player", "play"), "short_video": ("create_post", "plus"), "social_feed": ("create_post", "plus"),
    "messenger": ("new_chat", "edit"), "notes_todo": ("note_editor", "plus"), "habit_tracker": ("habit_edit", "plus"),
    "expense_tracker": ("expense_add", "plus"), "fitness_tracker": ("workout_player", "play"), "meditation": ("session_player", "play"),
    "recipe_app": ("cook_mode", "food"), "casual_game": ("game_play", "gamepad"), "photo_editor": ("editor_canvas", "image"),
    "ride_hailing": ("ride_options", "car"), "food_delivery": ("cart", "cart"), "quick_commerce": ("cart", "cart"),
    "marketplace": ("cart", "cart"), "classifieds": ("post_ad", "plus"), "travel_booking": ("trip_results", "search"),
    "hotel_booking": ("trip_results", "search"), "event_tickets": ("seat_select", "ticket"), "job_portal": ("job_list", "search"),
    "language_learning": ("lesson", "play"), "online_learning": ("course_detail", "book"), "property_portal": ("map_search", "pin"),
    "doctor_consult": ("slot_picker", "calendar"), "services_marketplace": ("slot_picker", "calendar"), "payments_app": ("scan_pay", "scan"),
}
