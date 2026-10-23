# WIRING for podcast
summary: Podcast Sahayak (podcast producer: episode pipeline idea -> booked -> recorded -> ready -> live with recording slots that never overlap, guests with a written release before anything goes public, run sheets from her topics, real ffmpeg loudness check against Apple's -16 LUFS / -1 dBTP and a normalised COPY on her word, transcripts ONLY from her audio (faster-whisper / Gemini / Lekhak hear) or her own SRT / VTT, show notes where quotes must be in the transcript and numbers not in it are dropped, chapters valid for Spotify and YouTube, music licence register, sponsor reads with ASCI #Ad at the start AND the end, invoices with a UPI link to HER UPI, Hoola's own RSS 2.0 + itunes + Podcasting 2.0 feed (transcript / chapters / person / guid / locked), cross-post drafts, analytics only from her exports; publishing, every guest / sponsor message and every invoice only on her tap)
db: app.podcast.models
router: app.podcast.api            (make_router(require_key, current_tenant) returns ONE router holding the key-protected /api/podcast/* routes AND two PUBLIC routes that check their own random feed token: GET /api/podcast/feed/{token}.xml and GET /api/podcast/pub/{token}/{ep}/{name}; only published, in-feed episodes and the show art are served)
tools: app.agent.podcast_tools     (PODCAST_TOOLS / PODCAST_LABELS / PODCAST_HANDLERS) ; voice: yes -> put BOTH `podcast` and `podcast_dekho` into voice.VOICE_TOOL_NAMES AND voice.VOICE_VIA_KAAM (v0.149 rule: calls hand Sahayak work to santosh_kaam)
employee: duty podcast_work = [podcast, podcast_dekho, file_read] {label "Podcast production", say "episode, guest booking aur release, run sheet, audio loudness, transcript, show notes / chapters, music licence, sponsor read (#Ad), invoice, feed (publish, guest / sponsor ko message, invoice aapki haan se)"} ; role podcast_producer {label "Podcast producer", duties [podcast_work, appointments, reminders, records, research]} ; preset podcast {label "Podcast / audio show", role podcast_producer, rules ["Quote, number, fees, tareekh kabhi mat gadho: transcript / unke shabd se hi.", "Har guest ki likhit ijazat (release) ke bina episode publish nahi.", "Sponsor read mein shuru aur aakhir dono jagah #Ad / sponsored.", "Licence saaf nahi to music nahi."]} ; READ tools: [podcast_dekho]
  - staff (staff:<id>) may add guests / episodes / run sheets / audio / transcripts / notes / music / reads and MAKE cards (invite, release request, sponsor message, invoice, publish); owner-only: settings, artwork, feed, release_got (recording her proof of the guest's yes), release_revoke, forget_guest, paid, posted, unpublish, and setting a sponsor fee. customer: actors are refused. No tool can decide a card: only POST /api/podcast/cards/{id}/decide (by_tap=True).
push: podcast_card -> ("Podcast: aapki haan chahiye", "{say}")     (only while data['card']['status'] == "waiting"; re-published on update: key by data['card']['id'])
push: podcast_alert -> ("Podcast", "{say}")
push: podcast_day -> ("Aaj ka podcast note", "{say}")
approvekey: not used (no money moves; the invoice card is a request she sends; sponsor fees are only her record)
worker: app.podcast.service.tick   (call every minute, e.g. `await asyncio.to_thread(podcast.tick)`; recording within 24 h (run sheet / release missing), recording passed 6 h without audio, publish date tomorrow, music licence ending in 14 days (once each); morning note once a day at her morning_time only when there is something)
prompt: PODCAST: podcast producer coworker (`podcast` / `podcast_dekho`). Transcripts come only from her audio or her own SRT / VTT file; show-note quotes must be in the transcript and numbers / facts not in it are dropped: never invent a quote, fee, date or listener number (her exports only). Every guest needs a recorded release before publishing; sponsor reads carry #Ad / sponsored at the START and the END (ASCI); music needs a clear licence. Publishing, any message to a guest / sponsor and any invoice are CARDS for HER tap: say "aapki haan ka card bheja hai", never "publish ho gaya / bhej diya". Use `podcast_dekho what=checks` before suggesting a publish.
persona: Podcast mein quote, fees ya listener number apne se kabhi mat bolo; publish, guest / sponsor ko message aur invoice ke liye "aapki haan ka card bheja hai" kaho.
flutter: PodcastScreen in lib/ui/podcast_screen.dart (+ PodcastEpisodePage) ; profile tile title "<name> · Podcast producer" subtitle "Episode, guest release, transcript, show notes, sponsor #Ad, feed" icon Icons.podcasts_rounded ; cards: podcast_card -> PodcastCardCard (also in calls: yes; key by data['card']['id'], update in place) ; podcast_alert, podcast_day -> PodcastNoteCard (also in calls: no). Widgets take (app:, data:) and use `app.api!.call(...)` and `app.api!.uploadFile(...)` (audio / artwork / captions / signed release / stats files), FilePicker (already a dependency), Native.openExternal, Clipboard.
features: podcast   (ffmpeg on PATH = loudness + normalise; without it everything else works and loudness says "naap nahi paya")
env: PUBLIC_BASE_URL (existing; needed for absolute feed / enclosure URLs). No new settings. Audio uploads go up to 400 MB in code, but nginx `client_max_body_size 30m` (deploy/nginx-santosh.conf) limits them: add `location /api/podcast/episodes/ { client_max_body_size 400m; proxy_request_buffering off; ... }` on the VPS for full-length WAV / video episodes (an hour of mono MP3 at 64 kbps is ~28 MB and fits today). Episode audio + artwork + releases are kept in data/podcast/<tenant>/ (chat files vanish in 24 h).
requirements: none (Pillow, reportlab, openpyxl, ffmpeg already used; faster-whisper optional via the existing VIDEO_WHISPER switch)
android: none
neighbours: editdesk (video editor desk: a video podcast's edit goes there), motiondesk (audiogram / animated clips), kalam (blog post from the show notes), influencer (brand deals for creators), artistmgr (music rights / IPRS registrations), patrakar (news podcasts: fact-check sheet), lekhak (hear = the Lekhak transcription fallback), videoedit (faster-whisper words / Gemini client reused), employee (UPI ID fallback), chatfiles (her files), indicpdf (Hindi / Marathi invoice names).
claude_md: |
  ## v0.1xx Podcast Sahayak: Hoola as a podcast producer ("Podcast producer" on the Employee page; Kala suite)
  - Owner's spec: episode pipeline, guest booking + release forms, run sheets, show notes / chapters / transcript from her audio,
    cross-post drafts, RSS / hosting checklist, sponsor reads with #ad disclosure, analytics she pastes. Waits for her Haan on:
    publishing an episode, any message to a guest or sponsor, any invoice.
  - Server `server/app/podcast/{rules,models,service,api}.py`, tools `podcast` / `podcast_dekho` (`agent/podcast_tools.py`, chat;
    calls via santosh_kaam), duty `podcast_work`, role `podcast_producer`, preset `podcast`, API `/api/podcast/*` (+ public token feed),
    app Profile > "<name> · Podcast producer" (`lib/ui/podcast_screen.dart`: Aaj / Episode / Guest / Sponsor / Music / Numbers / Niyam +
    `PodcastEpisodePage`), cards PodcastCardCard (`podcast_card`, also in calls), PodcastNoteCard (`podcast_alert`, `podcast_day`).
    Tests `server/tests/test_kala_podcast.py` (8).
  - Show: name, host, author, description, language, Apple category (from Apple's list), explicit, owner email (said plainly: PUBLIC in
    the feed), artwork checked against Apple (1400-3000 px square, JPG / PNG, RGB) and re-encoded from pixels (EXIF / GPS gone).
  - Episodes EP-001: idea -> booked (recording slot; two recordings never overlap incl. her gap minutes; past times refused) -> recorded
    (her audio, copied into data/podcast) -> ready -> published. Guests G-001 (bio = data, OTP / card numbers scrubbed). Run sheet from her
    topics: intro, guest intro from their own bio, topic blocks with questions (model only from topics + bio, else plain prompts), sponsor
    slots where she placed reads, outro.
  - Audio: ffmpeg loudnorm analysis (ITU-R BS.1770: integrated LUFS, true peak, LRA) vs Apple's -16 LUFS +/- 1 and true peak <= -1 dBTP;
    "Awaaz barabar karo" = two-pass loudnorm into a NEW 44.1 kHz MP3 (her original kept), re-measured.
  - Transcript ONLY from her audio (faster-whisper word times when VIDEO_WHISPER, else Gemini timed JSON, else Lekhak hear = one block
    without times) or her own SRT / VTT (Riverside / Descript / Audacity); speakers S1 / S2 renamed only to names she gives; files VTT /
    SRT / Podcast-Index JSON / text.
  - Show notes: summary + points + chapters + quotes from the transcript (model, else her own words); a sentence with a number not in the
    transcript is dropped, a quote is kept only if its words are really in the transcript (with its real time), chapters snapped to real
    segment starts, first at 00:00, >= 30 s apart, plain text, never past the end (= Spotify's and YouTube's rules); what was dropped is
    shown. Her edits re-validated. Description = #Ad line first when sponsored, summary, points, guests, chapters, links, music credits,
    AI label (IT Rules 2026) when she marked AI-made parts. Cross-post drafts (YouTube, Instagram, LinkedIn, X <= 280, WhatsApp,
    newsletter) she copies; nothing is posted.
  - Music / sound licence register M-001 (own / commissioned / CC0 / CC BY with credit / royalty-free / paid / unknown, proof, valid
    until): unknown or expired = publish blocked. Sponsors S-001 (her fee only; never guessed) and reads per episode (pre / mid / post):
    `add_disclosure` wraps her script with "#Ad / sponsored" at the START and the END (ASCI audio rule), risky claim words flagged
    (guarantee, 100%, cure, assured return ...), and when a transcript exists the real audio is checked for a disclosure near the
    brand's first and last mention (warning).
  - Checks before publishing (`checks`): blockers = no audio / title / show name, any guest without a release, unclear music licence,
    a read without #Ad at start + end, no / blank / stale show notes; warnings = chapters, no transcript, loudness, explicit not set,
    artwork, news / current affairs (IT Rules 2021 Part III note), brand approval not recorded.
  - Releases: starter wording (recording + edit without changing meaning + podcast platforms + promo clips; AI voice / face NOT included;
    copyright stays with her; fee only if she gives it) or her own; `release_request` card -> draft she sends; she records the yes
    (`release_got`, owner): signed file (kept), the guest's written reply (must say agree / haan / sehmat), or said on the recording (the
    transcript around her time code must hold consent words). Revoked -> the live episodes are named, republishing blocked.
  - Cards (`podcast_cards`: publish | invite | release | sponsor | invoice | message), a hash of what they show REBUILT from the state now;
    any change after the card = stale; the same waiting card is never made twice; ONLY `POST /api/podcast/cards/{id}/decide {yes, hash}`
    (by_tap) decides; publish re-runs the blockers at the tap. Publish -> status published + publish pack (show notes .md, transcript
    VTT / SRT, chapters JSON) as her files + cross-post drafts; with her feed on, the episode appears in Hoola's feed.
  - Hoola feed (her switch; random token, "naya link" kills the old one): RSS 2.0 + itunes (author, image, category, explicit, owner,
    type, episodeType, season, episode, duration) + Podcasting 2.0 (podcast:guid = UUIDv5 of the feed URL, podcast:locked with her
    owner email, podcast:transcript VTT + SRT rel=captions + JSON, podcast:chapters application/json+chapters, podcast:person host +
    guests with a signed release only, podcast:season / episode); enclosure / transcripts / chapters / art served only for published
    in-feed episodes; she submits the feed URL to Apple / Spotify / YouTube / JioSaavn herself. Unpublish (owner) takes it out at once
    and names the platforms where she must remove it herself.
  - Money: invoice POD/<FY>/001 for her agreed fee (refused without one), GST 18% with her GSTIN (CGST + SGST same state else IGST;
    her CA confirms), TDS note (brand may deduct under Income-tax Act 2025 s.393(1)); PDF + draft with a UPI link to HER UPI ID; "paise
    mile" + TDS recorded by her. Analytics: CSV / Excel exports (Spotify for Creators, Apple Podcasts Connect, YouTube Studio) parsed by
    column families; only her numbers; repeats skipped; best episode, low listen-through hint.
  - Worker `tick`: recording within 24 h (run sheet / releases missing), recording passed without audio, publish date tomorrow, licence
    ending (once each) + morning note. DPDP `forget_guest`: phone / email / bio / notes removed; the name and the release proof stay
    (record of what she published).
  - Research (23 Oct 2026): podcasters.apple.com/support/audio-requirements (around -16 LKFS +/- 1 dB, true peak <= -1 dBFS, ITU-R
    BS.1770-5; RSS: MP3 or AAC, AAC in MP4 recommended; mono 64-128 kbps / stereo 128-256 kbps at 44.1 / 48 kHz); Apple artwork 1400-3000
    px square JPG / PNG RGB (help.soundcloud.com "Ensuring podcast artwork meets Apple Podcasts requirements"); support.megaphone.fm
    audio specs (Spotify-owned host, 22 Apr 2024: -16 LUFS recommended, MP3 44.1 kHz); github.com/Podcastindex-org/podcast-namespace
    (phases 1-7 closed, transcript type text/plain | text/html | text/vtt | application/json | application/x-subrip with rel="captions",
    chapters application/json+chapters, podcast:guid UUIDv5 namespace ead4c236-bf58-58c6-a2c6-a6b28d128cb6 over the feed URL without
    scheme / trailing slash, https only); support.spotify.com/creators "Episode chapters" (first 00:00, >= 3, >= 30 s apart, plain text,
    Podlove chapters for RSS-hosted shows); support.google.com/youtube/answer/9884579 (first 00:00, >= 3 timestamps, each >= 10 s);
    help.podcast.co YouTube RSS ingestion (24 May 2023: not available to everyone, YouTube hosts copies, show art as the still image);
    ascionline.in/social/faqs (modified 26 Sep 2025: audio / podcasts disclose at the START and the END; labels #Advertisement, #Ad,
    #Sponsored, #Collaboration, #Partnership, #Employee, #Free gift, in English or the ad's language); CCPA "Endorsements Know-hows!"
    (Jan 2023; taxconcept.net 6 Mar 2023: live streams disclose in audio + video throughout); IT (Intermediary Guidelines and Digital
    Media Ethics Code) Amendment Rules 2026 (notified 10 Feb 2026, in force 20 Feb 2026: synthetic audio / video labelled, 3 h / 2 h
    takedowns, 7-day grievance; businesstoday.in 10 Feb 2026); atblegal.com (7 Apr 2026: written guest agreements for consent to record,
    edit, distribute and monetise; music licences, "royalty free" not always commercial; ownership needs written agreements with editors /
    co-hosts, cf. Copyright Act 1957 s.17); Copyright Act 1957 s.38 (performers' rights) and s.52 (fair dealing: narrow, Hoola never
    relies on it to clear music); IPRS / PPL licensing for commercial music (cleartax.in license-play-music, Apr 2025). GST 18% and the
    s.393 TDS line are notes for her CA, not tax advice; the release wording is a starter, not legal advice.
not_verified: Flutter screen + cards not compiled here (no Flutter SDK): check CI analyze annotations for lib/ui/podcast_screen.dart (Dart 3 records in `_form`, switch expressions, `Iterable.firstOrNull` from package:collection-free Dart 3.0+, `api.uploadFile` with an empty byte list for the text / audio release path). Real Gemini timed transcription and faster-whisper were not run here (tests replace `_engine_transcribe`); Gemini's segment times on long (1 h+) audio may drift: her SRT / VTT from the editor is the exact route. The real model never ran (tests stub `_model_json`). The feed was checked as XML with ElementTree and against the namespace rules, not through Apple's / Spotify's validators (submit once with Podbase / Cast Feed Validator). Byte-range requests for the enclosure rely on Starlette's FileResponse (Range support in current Starlette); behind nginx large-file streaming / caching was not tried. YouTube RSS ingestion is not open to everyone (pilot) and India availability was not confirmed. Large uploads above nginx's 30 MB need the location override above.
