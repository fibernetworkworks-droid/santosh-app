# HeyGen web app (app.heygen.com): IA and visual design map, as of 11 Nov 2026

## How to read this

I could not log in, so nothing here comes from seeing a rendered, authenticated screen. The strongest evidence is HeyGen's own publicly served app files, which I fetched directly:

- **[S1]** English string catalogue, 72 namespaces, about 1.9 MB: `https://app.heygen.com/locales/en-US.json`
- **[S2]** App shell HTML: `https://app.heygen.com/home`
- **[S3]** Design-token stylesheet: `https://app.heygen.com/main-BF95IqJp.css`
- **[S4]** Main bundle, which holds the sidebar, sub-nav and app registry code: `https://app.heygen.com/main.app-Cm0VXWER.js`
- **[S5]** Home layout bundle: `https://app.heygen.com/home_layout-D6cFwp0e.js`

The hashed filenames in S3–S5 change on every deploy; start from S2 to find the current ones. Local copies are in `(session scratch, not kept)` (`en.json`, `main-BF95IqJp.css`, `main.app-Cm0VXWER.js`, `home_layout-D6cFwp0e.js`).

Other sources: the help centre (`help.heygen.com`), HeyGen's monthly release blog, HeyGen Academy, and one third-party screenshot catalogue, saasui.design.

Labels used throughout:
- **CONFIRMED**: in an official HeyGen source (help centre, blog, Academy, or S1–S5).
- **REPORTED**: third party only.
- **INFERRED**: my reading of how confirmed pieces fit together.

Two caveats on the bundle evidence:
- The catalogue contains strings for several coexisting Home variants (`home_v2`, `home_v4`, `home_v5`, `home_lobby`) and many feature-flagged items. A string existing proves the screen exists in code, not that every account sees it.
- Exact pixel layout of most pages is not derivable from strings. Where I describe layout, the source is a help article, the Academy, saasui captions, or CSS classes, and I say which.

---

## 1. Global shell

### 1.1 Left rail (primary navigation)

CONFIRMED from S4 (`HomeSidebar.tsx`, component `StandardHomeSidebar`) with labels from S1.

The rail is a 78px-wide icon column. Each item is a 40×40 tile with 12px radius and a 24px icon, with an 11px/16px semibold label underneath. The tile scales to 110% on hover. There is a compact mode where labels collapse and appear as right-side tooltips.

Order in code:

| # | Label | Route | Colour scheme | Notes |
|---|---|---|---|---|
| 1 | Home | `/home` | green→cyan gradient label when active | Always present |
| 2 | Explore | `/explore` | brand cyan | Flagged |
| 3 | Avatars | `/avatar/...` | brand cyan | Shows a status badge while an avatar is generating or ready |
| 4 | Video Agent | `/video-agent` | agent cyan `#04d3d6` | Flag-dependent |
| 5 | Brand | `/brand` | "magic" scheme | Flag `sidebar-brand-nav` |
| 6 | Grow or Publishing | `/grow`, `/publish` | green `#35c838` | Flagged; rocket or calendar icon |
| 7 | Apps | `/apps` | grey `#636959` | |
| 8 | More | hover popover | — | Overflow items plus "Customize navigation" |
| 9 | Developers | `/developers/api` | grey | Hidden for visitors; nudge "New home for all things developer" |
| — | divider | | | |
| 10 | Projects | `/projects` | grey | |
| bottom | Plan CTA | | | See below |

- **More popover:** "Customize navigation" opens a checklist that hides or shows rail items, with a "Done" button. Hidden items are saved per user (`nav_hidden_ids`).
- **Plan CTA** (`SidebarPlanCTA.tsx`), by plan:
  - Free: "Plans & Pricing" with a circular progress ring and tooltip "You have {count} free videos left".
  - Creator / Pro: "Plans & Pricing".
  - Business / Team / Enterprise: "Invite to workspace".
- **Active state:** the icon tile fills with the scheme colour, white icon, inset glow (`inset 0 0 10px #a9ffe2`). Inactive is text-body grey; hover is a 15% tint.
- **Other rail strings in S1** whose placement I could not pin down: "Collapse navigation", "Expand navigation", "Toggle navigation", "Translate", "Originals", "Watch Later", "Upgrade to Create Videos", "Trial expired / Upgrade now", "Create a team", "Use HeyGen via MCP" (Connect ChatGPT / Connect Claude / Other agents).

REPORTED (saasui.design): distinct screens for Home, Video Agent, AI Studio, Video Translate, Single Scene, Avatars, Voices, Brand Systems, App Library, Integrations, Projects. https://www.saasui.design/application/heygen

Older or alternate IA still present in S1 (`SideMenu` namespace) and in help articles: a "Create" group and a "My HeyGen" group, "Create Video", "Templates", "Translate", "Tools", "Trash". The Feb 2026 release replaced the old home with "clearer navigation and dedicated spaces for different creation paths". The in-app tour for that change says "Video Agent, Single scene, AI Studio and Translate moved out of the sidebar and into…" (string truncated in my dump; destination looks like the Home "Apps" row) and "Your recents moved out of the sidebar and onto the main view". Sources: https://www.heygen.com/blog/heygen-february-2026-release, S1 `Home.home_upgrade_tour_*`.

### 1.2 Secondary navigation (per-section sub-nav)

CONFIRMED from S4 (`HomeSecondaryNav.tsx`, config function). Each section opens a second panel with a title and items. A 286px-wide panel slot is in S5; INFERRED that this is the sub-nav width.

- **Avatars** (title "Avatar videos"; alternate title "Manage Avatars"):
  - Group 1: Avatars (`my-avatars`).
  - Group 2: AI Studio (`studio`), Avatar Shots, Voices, Templates (conditional), Brand Systems (`brand-system`, when no Brand section), PPT/PDF to video, Interactive video.
  - Alternate ordering under a flag: Avatar Shots; then Avatars and Voices; then a "Create Video" group with AI Studio.
  - "Manage Avatars" variant: Avatars, Design a look, Voices.
- **Brand:** Brand Systems, Brand Templates, Brand Glossary.
- **Apps:** Home, Integrations.
- **Tools** ("Create with Tools", older): Home, Integrations, Product placement, AI Clipping, Batch mode, Video podcast, Face Swap, Generate AI Video, Generate images.
- **Developers:**
  - Overview, Billing (non-enterprise admins), Usage, Models, Webhook, Connections.
  - Divider, then external links: API Doc, MCP, CLI, Skills, Changelog (all to developers.heygen.com).
  - S1 also has "Workflows", a node-graph builder with Select and Hand tools, Publish, Run, and "All changes saved".
- **Grow** (S1 `grow_nav_*`): Create, Inspire, Connect, Schedule, Analytics, AI Business Card. Routes `/grow/create|inspire|connect|schedule|analytics|leads`.
- **Projects, Video Agent, Home:** no sub-items in this config.

### 1.3 Top-right chrome

CONFIRMED from S5 (`TopRightNav.tsx`) and S4.

- A floating cluster of pills: 40px high, fully rounded, `fill-general` background, elevated shadow, 12px gaps.
- **Search:** a 32px round icon button that expands to a 224px inline input. Placeholder "Search for videos or features". Result tabs: All, Recents, Tools, Projects. Empty state "Start typing to search"; no-match state "No results found". "Clear search" button.
- **Notifications button** (lazy-loaded `top_right_notification_button`). The Dec 2025 blog confirms: bell → "What's new" changelog with email subscribe. https://www.heygen.com/blog/heygen-december-2025-release
- **Orby assistant pill** (`OrbyNavButton.tsx`, `OrbyDockShell.tsx`): opens a docked side panel.
  - Tabs: Chat, Updates (with unread count), Support.
  - Time-of-day greetings such as "Good morning, {name}."
  - Live status titles: "Working on your video…", "{n} videos are ready".
  - Deep-link action buttons: "Open Plan & Billing", "Open the voice panel", "Open Look Studio", and similar.
  - REPORTED: "Ask Orby — AI assistant side panel with greeting and suggested actions" (saasui).
  - June 2026 blog confirms an "in-app customer support agent". https://www.heygen.com/blog/heygen-june-2026-release
- **Credits:** a `CreditUsageRing` component exists, with strings "You have {count} credits left", "Get more credits", "Credits · {count} left". INFERRED: credits appear in the account menu and/or the plan CTA. I could not confirm a standalone top-bar credit counter.
- A top banner slot exists for payment failure, enterprise contract expiry and promos.

### 1.4 Account menu

- **Location, CONFIRMED:** bottom-left "box with your initial"; click or hover → Settings. https://help.heygen.com/en/articles/8300888-how-to-manage-your-heygen-account-settings
- **Items, CONFIRMED from S1 `Account` namespace** (exact order unknown): My Profile / "Complete your profile"; workspace block ("Workspace", "Personal", "Change Workspace", "Back to my workspace", "Manage Workspace", "Add Account"); plan tier label (Free / Creator / Pro / Team / Business / Enterprise / "{plan} Plan Trial"); "Credits · {count} left"; "Get more credits"; "Upgrade" / "Upgrade Plan" / "Upgrade to Teams" / "Plans & Pricing"; "Settings"; "Personalization"; "Help Center"; "Learning & Community"; "Resources"; "Entrepreneur Program"; "Cookie preference"; "Terms"; "Privacy"; "Log out".
- REPORTED: "profile popover with workspace plan, upgrade, settings, help and log out" (saasui).

### 1.5 Create menu

CONFIRMED from S1 `CreateMenu` namespace, 24 entries. Whether it currently renders as a single dropdown is unverified; the redesigned Home spreads these across cards.

- Create a video; Create in AI studio; Use a template; Import a PPT/PDF; Video agent; Photo to video; Quick avatar video; Translate a video / Video dubbing / Audio dubbing; Batch mode; Automated video series; AI Clipping; Product placement; Interactive video; Interactive avatar; Motion Designer; Apps.
- Create an avatar: Create your digital twin; Photos to avatar; Generate an avatar.
- A "Premium" badge string exists for premium entries.

Help-centre wording for the older flow: "Create in the left-side menu → Create a Video → choose Landscape or Portrait → start from scratch / photo to video / template / upload PPT/PDF / video agent". https://help.heygen.com/en/articles/11049655-overview-our-new-ai-studio

---

## 2. Page by page

### 2.1 Home (`/home`; sub-routes `/home/create|projects|apps|avatar|studio|translate|video-agent|photo-to-video|tools`; verticals `/home/real-estate|finance|health|legal|business`)

**Purpose:** launch pad. Pick a workflow, see your avatar's status, resume recent work. Several variants coexist.

**"Lobby" variant** (CONFIRMED S1 `home_lobby_*`; the Avatar Shots help article calls it "the new HeyGen lobby"):
- Greeting "Hi {name}, where do you want to start?" with subtitle "Pick a workflow to get started, or continue where you left off."
- Workflow cards, each with title, one-line description and an arrow label such as "→ AI Studio". Cards seen in strings:
  - Generate a video from a prompt (Video Agent)
  - Build a video scene by scene (AI Studio)
  - Make an avatar video from script
  - Make an avatar video from a photo
  - Create your avatar
  - Start with a template
  - Translate any video (175+ languages)
  - Enhance any video to 4K (Upscale)
  - Clone your voice
  - For Agents and Developers (→ API)
  - Place your Avatar in any scene (Avatar Shots)
  - Enterprise extras: PPT/PDF to Video, Interactive Video ("Boost Your Engagement"), HeyGen Tutorials
- "Avatars" strip with "Create avatar · Create new" and "See all".
- "Recent creations" with tabs Recent / Drafts and "See all projects".
- Empty states: "No recent videos yet", "No drafts yet", "No recent creations yet · Your recent videos will appear here · Get started by creating your first video!".

**"v4" avatar-first variant** (CONFIRMED S1 `home_v4_*`, `mission_pod_*`):
- An avatar "mission pod": a three-step setup card.
  - Step 1 Create Avatar; Step 2 Tune Avatar (Voice / Motion); Step 3 Create Video.
  - Progress "{done} of {total} complete". Status chips: Complete, Incomplete, Generating…, Failed, Needs verification, Moderation rejected, Appeal under review, High/Low Quality.
  - Actions: Change avatar, Change Look, Change Voice, Improve Avatar, Meet Your Avatar.
  - Video creation stays locked until the steps pass, with messages such as "A voice is required to create a video".
- "Create" row of app tiles: Video Agent "Describe it, and AI builds the video"; AI Studio "Build your video scene by scene"; Single scene "One scene with your avatar, from a photo"; PPT/PDF "Turn slides into an avatar video"; Translate.
- "Ideas for you" row: personalised script ideas showing "~{seconds} sec", "Why this?" and "Use this script". "Customize → Personalize" opens a form (Your work, About your business, Audience, Favorite topics, Anything else, "Import from AI", Video length).
- "Recent Videos".
- Empty state: "Create your avatar once. Use it in endless videos." with CTA "Create My Avatar".

**Prompt hero (Video Agent on Home)** (CONFIRMED S1 `video_agent_*`, `prompt_builder_*`):
- Headings "Create your avatar video" / "what will you create?".
- Prompt input, placeholder "Describe the video you want ...".
- Suggestion chips: Team announcement, Event invitation, Explain an idea, Share an internal update, Product demo, Sales pitch, Social media content, Customer testimonial, Training tutorial, Create a UGC-style ad.
- Prompt-builder "Add inspiration" hub with categories Intros, Captions, Format, Brand (Presets / Your brand systems), Recreate ("Reference any video. Make it yours.").
- REPORTED: "prompt composer with avatar, voice and brand chips plus use-case template tabs" (saasui).

**Other Home elements** (CONFIRMED S1):
- Banner carousel with "NEW" badge: "Avatar V is here", "Avatar Shots with Seedance 2", "Beyond the studio. Meet the apps."
- "Shortcuts" section: "Pre-built workflows to simplify common video tasks".
- First-run tour "Home just got an upgrade · {count} quick stops · About 30 seconds".
- Onboarding checklist cards: "Create your first video / Generate your digital twin / Translate a video". REPORTED: "welcome dashboard with 3/4 account setup checklist cards and video prompt templates" (saasui).
- Vertical homes for Real Estate, Finance, Healthcare, Legal and Business with hero lockups ("for Real Estate") and use-case tabs. Confirmed by the Aug 2026 blog: https://www.heygen.com/blog/heygen-august-2026-release

### 2.2 AI Studio start page and editor (`/create-v4/draft`, `/avatar/studio`)

**Start page.** REPORTED: "scene-by-scene start page with new video tile, existing draft and template gallery" (saasui). CONFIRMED strings: Blank Landscape / Portrait / Square Video; "Use an AI Studio Template".

**Editor arrangement.** HeyGen is explicit that this is script-first, not timeline-first: "HeyGen AI Studio is script-focused, not timeline-based". https://help.heygen.com/en/articles/11049837-create-your-first-video-in-our-studio

- **Left: script panel.** One block per scene.
  - Below it: "+ Scene" (Blank Scene / Add from Template), Pause (± 0.5 s), Upload Audio / Record Audio, Voice Director (megaphone icon).
  - Scene "⋯" menu: Regenerate Audio, Render Scene, convert to voice mirroring, Translate, Delete.
  - Text-selection popover: Comment, Gesture, Pronunciation.
  - Slash commands ("Type `/{command}` on the script").
  - Selecting a canvas element shows two draggable timing markers in the script that set when it enters and exits.
  - Limit guidance: under 2,000 characters per scene; "Auto-split" for long text.
- **Centre: canvas ("work board").** Clicking the avatar opens look, framing (Original / Close up / Circle), remove background, corner radius, animations. Zoom controls and "Fit to screen".
- **Above the canvas / toolbar:** an "Avatars" tab, plus visuals tools for text, media, elements, AI images, captions and background colour. Toolbar strings: "Avatar", "Brand".
- **Right: tool menu and Properties inspector.**
  - Help article order: Avatar, Script (voice), AI, Media, Text, Music, Stylized Captions, Templates, Layers; also Interactivity, Recorder and Brand.
  - S1 tab strings: Media, Text, Elements (with "Generated"), Captions, Music.
  - Nov 2025 release: "More Options" context menu replaced by a unified "Properties" panel; "Avatar & Voice" panel.
  - Sources: https://help.heygen.com/en/articles/11049655-overview-our-new-ai-studio, https://www.heygen.com/blog/heygen-november-2025-release
  - REPORTED: "script panel, avatar canvas preview, scene timeline and Avatar & Voice settings" (saasui).
- **Bottom: scene timeline.** One card per scene.
  - Playhead, total duration, drag to reorder.
  - Arrow between clips adds a transition; "⋯" → Duplicate Scene; add template / video / premium-slide scenes.
  - Show or hide timeline; multi-select mode ("{count} selected", Merge scenes, Split Scene).
  - Track colours in S3: music cyan `#00c4ff`, captions pink `#f3a6ff`, text green `#35c838`, SFX orange `#ff8c42`.
- **Top bar.** Source: https://www.heygen.com/academy/ai-studio/how-to-create-a-new-project
  - Project name.
  - Hamburger menu: Save as Template, Upload / Download script (.txt, .docx, Excel/CSV), Version history (Restore / Delete this version), Contact support, Tutorials, Theme (Light / Dark / Sync with system).
  - Orientation switch, Brand kit picker, Feedback.
  - Save status, "Invite Members", notifications and comments.
  - Preview, Generate.

**Panels in detail** (CONFIRMED S1 `TextEditorV4`):
- **Avatar:** "Choose Avatar & Look", Looks, Replace avatar, "Add avatar to all scenes", Avatar Background, Framing, Motion Engine (Avatar III / IV / V), Advanced Settings (custom motion prompt, motion reference).
- **Voice:** Select Voice, Voice Engine, Language, Accent ("Original accent"), Speed, Pitch, Volume, Similarity, Stability, Style, Speaker boost. "Delivery style": Enhance voice / Direct voice / Mirror voice. "Apply to all scenes". "Edit Voice" / "Improve this voice" (Voice Doctor). "Avatar Level Voice" vs "Scene Level Voice".
- **AI Tools:** Script Writer (quick actions Shorter / Longer / More engaging / More professional; "Version {n} of {m}"; "Add as new scene"), Image Generator, Video Generator, Motion Designer, AI Edit.
- **Media:** tabs All / Assets / My Media (Uploaded / Generated) / Stock Media / Image / Video / SVG / Music / Generate. Actions: Set as background, Detach from background, Replace media, Crop, Trim, Loop / Freeze / Fit to scene, "Play original audio".
- **Text:** Title, Body, Headlines, Name Cards; font ("All Fonts", "Brand Kit Fonts"), bold / italic / underline / strikethrough / uppercase, alignment, text colour, background colour, outline, shadow, opacity.
- **Elements:** Shapes, Icons, Stickers, Frames, Logos, Motion Elements, "Brand Design Element".
- **Captions:** tabs Style / Customize; words per line, position, "Apply to all scenes", "Fix caption words", "Motion captions".
- **Animation:** In / Out with Fade, Slide, Rise, Pop, Wipe, Grow, Shrink, Blur, Appear; "Separate enter & exit"; Pan & Zoom; camera speed Slow / Fast / Instant.
- **Layout:** Split 35/65, Split 50/50, Cover, Floating, Floating rounded.
- **Layers:** Bring to top, Send to back, Group / Ungroup.
- **Music:** library moods Happy, Instrumental, Playful, Calm, Dramatic, Inspiring; My music; Upload; Sound Effects.
- **Interactivity:** Branching (switches to a branch view), Action button (URL / Jump to scene), Quiz; tabs Content / Appearance; "Wait for click" toggle. https://help.heygen.com/en/articles/13538881-how-to-use-heygen-s-interactivity-for-branching-and-clickable-videos
- **Recorder:** mic on/off → Start Recording → pick screen, tab or window → trim or split into scenes. https://help.heygen.com/en/articles/14251628-how-to-use-screen-recorder-in-ai-studio
- **Translate:** "Translate script", "Translate text on the canvas", "Translate as new draft".

**Preview.** Audio and script preview only: "Final lip-sync shows after video is generated". "Render Scene" produces a per-scene lip-sync preview, with a "Free Preview" allowance.

**Generate dialog** (titled "Generate Video", button "Submit"):
- Fields: Title; "Save to" folder (My Projects / My Videos); Resolution (720p / 1080p / 2K / 4K, plan-gated); FPS (25 / 30 / 60; "Dynamic FPS"; higher FPS needs a subscription); Format (MP4 or WebM with transparent background); HeyGen Watermark On / Off.
- Credit readouts: "This uses {duration}s of Avatar generation time" / "Generate for {credits} credits".
- Upsell card: "Upgrade to unlock the best of video creation".
- Pre-submit warnings such as "Alert: No Avatar in Video".
- Sources: S1; https://help.heygen.com/en/articles/13007313-ppt-pdf-to-video; https://help.heygen.com/en/articles/13466178-how-to-use-templates-in-heygen-to-streamline-video-creation

**Collaboration.** Single Editor Mode: first opener edits, others view. "Request Access" in the toolbar; presence indicator at the top of the file; comments. Draft-occupied dialog: "The draft is being edited · Edit here / Try again / Go back". https://help.heygen.com/en/articles/13540469-single-editor-mode-collaborate-on-video-projects-in-real-time

**Second editor: "Studio Neo" / Story editor** (CONFIRMED in S1 `StudioNeo`; where it surfaces is unverified).
- Word-level transcript editing for recorded footage: "Enter to split. Backspace to merge scenes."
- Per-selection bar: Media, Camera, Sticker, Layout, Graphic, "Add on top".
- Scene layouts: Fullscreen Avatar, Fullscreen Media, You in a bubble, Split screen, Green screen.
- Captions On/Off with style gallery; background music toggle; finish screen "Looks good on you. · Export video".

### 2.3 Avatars (`/avatar/my-avatars`, `/avatars`, `/avatars/looks`, `/avatar/design-look`)

**Library.**
- REPORTED: "My Avatars grid showing the user's digital twin with looks" and "public avatar library with category filters and grid/list toggle" (saasui).
- CONFIRMED S1: filter tabs All, Recommended, Favorites, Professional, Lifestyle, UGC, Community, Expressive, AI-generated, Hyper Realistic; "Filters" button; "Look Packs"; "Enterprise Templates".
- Card: favourite heart, select, "More actions" (Rename, Replace, Delete, Reset Verification, Update profile picture, Share to other workspaces).
- Tags: IV, Expressive, Premium, AI / AI Photo, Community-Submitted, Swappable Outfit, Studio, Expiring, verified.
- Home strings: "Explore 500+ avatars".
- Empty state: "Create your first avatar".
- Dec 2025: "Simpler avatars experience… from a single view".

**Avatar detail page** (CONFIRMED S1 `avatar_details_*`):
- Tabs Looks / Voice / Motion, each with explainer copy ("How {name} appears in a video…").
- "Next steps" card "{n} of {total}": Add voice, Listen to voice, Teach how you move, Verify motion, Create a new look.
- "Improve your avatar" menu: A look / Voice / Motion.
- "Use in a video" → "Build scene-by-scene" / "Quick create" / "Create with Video Agent". https://help.heygen.com/en/articles/10034438-how-to-get-started-with-photo-avatars

**Looks.**
- "Create new look": Upload a photo; Generate with AI ("Describe an outfit or scene, or remix with a template"); Take a photo; Continue on your phone.
- Help article also lists webcam, Google Drive, Instagram, YouTube, TikTok, other link, record via phone.
- Edit an existing look:
  - Appearance presets Refine / Studio / Glow, plus Advanced sliders and "Save as new".
  - Camera angles; Custom Edit by prompt; "Remix into a Scene".
  - Edit Look retouch slider (Aug 2026).
- Look Packs: persona-based sets (June 2026).
- Personal Model: toggle in the Generate Looks prompt bar → pick 10 to 30+ photos, quality indicator → Train (60 credits, 10–15 min).
- Sources: https://help.heygen.com/en/articles/9964694-avatar-looks-explained; https://help.heygen.com/en/articles/14896977-personal-model-train-your-model-to-create-better-looks

**Avatar Shots** (opens by default under Avatar): Presenter / Cinematic modes at top; Create / Explore.
- Prompt area with up to 3 avatar thumbnails ("+" to add, grey "x" to remove).
- Optional reference media.
- Bottom pills: Duration 5 / 10 / 15 s, Orientation, Enhance. "↑" to generate.
- Outputs stay in the Avatar Shots section, not Projects.
- https://help.heygen.com/en/articles/14448006-avatar-shots-powered-by-seedance2

### 2.4 Avatar creation wizards (`/avatars/create/avatar-hub`, `/avatars/create/digital-twin/lite-record|lite-upload|…`)

**Entry.** Avatar > Avatars > "New Avatar" → "Clone a real person" (Avatar V) or "Create a virtual character" (→ "Upload photo" / "Design with AI"). CONFIRMED help. Home shortcuts: "Clone me · Takes 15 seconds!", "Use a photo · Upload image", "Build an avatar · Describe it to life".

**Avatar hub flow** (CONFIRMED S1 `avatar_hub_*`; step order INFERRED from string sequence):
1. **Appearance.** "Add a photo you love": upload, take one now, upload from phone.
   - Guidance: Facing the camera / Clear, even light / Just you in frame. Avoid: Group shot / Looking away / Too far away.
   - Validation states: no face, multiple faces, face too small, resolution too low; "Continue anyway".
   - A non-person photo offers "Continue as a character".
   - Name the avatar.
2. **Motion** (optional but pushed).
   - Intro "Next, we'll need a recording of you" and "Why a recording?".
   - Guideline carousel "Good footage · Tip {n} of {total}": no need to be camera-ready, stay centred, speak with energy.
   - "Motion studio": camera picker, Portrait / Landscape, language, scripted ("We'll give you the words") or free style, "{seconds} sec minimum".
   - Live camera checks: face in oval, too dark, virtual camera, covered lens.
   - Or "Record on phone" via QR, or upload a video (15 s to 10 min).
   - "Review your recording"; identity-mismatch notice.
   - Skip warning: "Your avatar won't look or move like you · Record 30 seconds / Skip anyway".
3. **Consent / verification.** See below.
4. **Voice.** "Finally, set your avatar's voice": voice guideline tips; "Clone your voice from this recording?" listen gate; Re-record / Use another voice.
5. **Complete.** "We're creating {name} · This usually takes 2 to 5 minutes" → "View my avatar".

**Older "lite" flow** (CONFIRMED help): screen "Create your Avatar in 15 seconds"; record via webcam, record via phone (QR or link), or upload footage (MP4 / MOV / WebM up to 10 GB, or Google Drive link); "Create Avatar". https://help.heygen.com/en/articles/12089286-create-your-first-digital-twin-video-avatar-with-avatar-iv

**Consent step** (CONFIRMED S1 `AvatarConsent` + help):
- Copy: "To prevent misuse of technology, we just need to confirm the person in the video is you."
- Spoken script with a one-time passcode: "I consent to HeyGen creating my AI avatar. For safety purposes, my unique code is {passcode}."
- Three methods: Upload Consent Video (drag and drop), Laptop Webcam, Smartphone (QR). Must be under 30 s.
- Camera and mic permission primer.
- "Continue without verifying": "You can preview and edit this digital twin, but can't use it until verified."
- Guest co-host consent pages; rejection reason shows on the avatar card.
- https://help.heygen.com/en/articles/12092609-recording-your-consent-video

**Photo Avatar "Design with AI".** Fields: name, age, gender, ethnicity, appearance, orientation, pose, style. Free plan: 3 photo avatars. https://help.heygen.com/en/articles/10034438-how-to-get-started-with-photo-avatars

**Single Scene / Photo to Video / Quick create** (Avatar IV / V).
- Presenter mode: script or audio, voice, engine III / IV / V, Custom Motion prompt, orientation, Generate.
- Cinematic mode: avatar or reference, prompt, Enhance Prompt, duration Auto or Custom 4–15 s.
- https://help.heygen.com/en/articles/12623520-animate-your-avatar-from-a-photo-using-the-single-scene-tool
- REPORTED: "avatar script composer with motion, voice, aspect ratio and empty recent creations" (saasui).

**UGC / product avatars.** Covered by the Product Placement app (2.11) and "UGC ads" strings ("Create engaging UGC-style video ads").

### 2.5 Voices (`/avatar/voices`)

- **Library.** Tabs "My voices" / "Public voices". Create actions: "Create your HeyGen voice" (Clone), "Design a voice", "Integrate 3rd party voice". https://help.heygen.com/en/articles/9834925-how-to-get-started-with-voices
  - REPORTED: "my voices list with clone, design and import voice actions" (saasui).
- **Filters** (S1): search, language, accent, Gender, Voice age, Use cases, Emotion, Favorites, avatar.
- **Voice card:** badges (Voice Clone, PVC / Professional Voice Clone, Voice Design, Imported, Public, Shared, Popular, Multiple speakers); "{duration} source audio"; "Updated {time}"; "Created by {name}"; favourite; emotion selector (Default / Original / Customize); "Edit voice"; "Improve this voice"; menu Rename / Share / Collaborators / Restart / Delete; bulk select and delete.
- **Empty state:** "Let Your Unique Voice Shine Brilliantly".
- **Instant clone modal:** record (mic check, device picker), record on phone via QR, or upload; "Keep ambient sounds in my recording"; "Creating your voice clone"; "Choose your favorite" among generated engine variants; rating prompt "How does this voice sound?".
- **Professional Voice Clone:** "Clone your voice" → "Professional Voice Clone" → upload up to 30 files / 1.5 GB, at least 20 min of speech → train 20–30 min. Paid add-on, $29/month per voice. https://help.heygen.com/en/articles/17589678-how-to-create-a-great-professional-voice-clone-pvc
- **Voice design:** "Describe your new voice" prompt, "Try a sample", "Generate voices" → "Generated voices" list, "Regenerate voices".
- **Voice Doctor:** chat-based refinement in an "Edit Voice" panel beside the player. https://www.heygen.com/blog/heygen-december-2025-release
- **Third-party integration:** provider and API-key table (ElevenLabs and others), "Import to HeyGen".
- **Settings:** speed, volume, pitch, inflection; similarity / stability / style and speaker boost (engine-dependent); accent / locale; engines (ElevenLabs v2 / v3 / v4, Fish, Panda, Starfish, Orca; HeyGen Voice from Oct 2026). https://help.heygen.com/en/articles/11202248-using-voices-in-the-ai-studio; https://help.heygen.com/en/articles/16139180-advance-voice-settings
- Note: the standalone Voices tab was folded into Avatar, AI Studio and Proofread in Nov 2025. https://www.heygen.com/blog/heygen-november-2025-release

### 2.6 Templates (`/templates`, `/brand/templates`, `/template/:id`)

- **Location:** Brand tab → Brand Templates; "Browse all templates or filter by use case". https://help.heygen.com/en/articles/13466178-how-to-use-templates-in-heygen-to-streamline-video-creation
- **Gallery strings** (S1 `Templates`):
  - "All Templates", "HeyGen Library", "All Categories", "All Styles", "Filter by category", search.
  - Orientation filter All / Landscape / Portrait.
  - Categories: Business, Education, Entertainment, Marketing, Learning & Development, News & Updates, Podcasts & Interviews, Sales & Marketing, Cinematic, Handmade, Iconic Artist, Pop Culture, Print, Retro Tech.
- **Brand banner:** "See all templates in your brand styling".
- **Detail view:** metadata rows (Avatar, Captions, Concept, Duration, Language, Media, Music, Orientation, Resolution). Actions: "Create from Template", "Draft this template with AI", "Customize in Video Agent", "Edit in Studio", "Build scene-by-scene".
- **My templates:** "Create Template", Edit, Duplicate, Make Public / Private, Collaborators, Get Template ID, Delete. Empty state: "No templates found · Create Your First Template".
- **"Explore" gallery** (`/explore`): "Recreate a video that works with your topic", featured examples, "Recreate" on each tile.
- Oct 2026: refreshed library, B-roll editor, stronger previews. https://www.heygen.com/blog/heygen-october-2026-release

### 2.7 Brand (`/brand`, `/brand/templates`, `/brand/brand_glossary`)

- **Brand Systems page:** tabs "All Brand Systems" / "Your Brand Systems"; "Add new" tile. REPORTED: "brand kit cards with add-new tile and saved brand kits" (saasui). Card menu: Rename, Duplicate, Copy as new, Set Cover, Collaborators, Trash / Restore.
- **Empty state:** "Create a Brand System to stay visually consistent".
- **Create:** paste a website URL → Import (detects logos, colours, fonts, assets, motion); or pick from a preset gallery (category tabs General, Personal Brand, Course & E-Learning, Corporate Training, Creator Channels, Real Estate; style groups Modern, Minimal, Bold, Elegant, Playful, Retro, Professional) → "Save this Brand System" / "Customize".
- **Inside a system:** tabs Brand Spec, Assets, Logos, Motion, Avatars.
  - Brand Spec: left panel has Colors (picker or HEX) and Fonts (Body, Caption, Display, Heading, Heading 2); right panel shows a live "Frame Compositions" preview.
- **Ready modal:** "Your Brand System is Ready → Create with Video Agent / Open in AI Studio / Start with a Template".
- **Brand Glossary:** A–Z term list with search and filters. Each term has Pronunciations and Translations tabs. "New pronunciation" (type or record, "Hear it in a phrase"); "New translation" (target language or All languages; "Don't translate" / force translate); Import / Export CSV or XLSX.
- Sources: https://help.heygen.com/en/articles/9889198-how-to-create-a-brand-system; https://help.heygen.com/en/articles/8830251-how-to-use-brand-glossary
- Not present: a "brand voice" text field or intro/outro fields. I found neither in help or strings.

### 2.8 Projects (`/projects`, `/projects/avatar-videos`, `/projects/trash`, `/assets`)

- **Tabs** (S1 `Project.tab_*`): Avatar Video, Agent, Translations, Apps, Assets / Media, Proofread Requests, Shared with me, Search.
- **Filter chips:** Drafts, Completed, Avatar Videos, Batch Videos, Video Agent, Video Agent Edits, Face Swap, Proofread, Generated, Uploaded; file-type chips Video / Image / Audio / Others.
- **Views:** Grid View / List View / Date View. Sort by Creation Date or Last Modified, ascending or descending.
- **List columns:** Thumbnail, Name, Type, Duration, Created, Edited, People with access, Actions.
- **Type labels** include Avatar Video (draft), Video Agent Session, Translation, Avatar Shots, Podcast, HyperFrames, Interactive Video, Speech Cleanup, Video Upscaler.
- **Folders:** "+ Folder" at top-left; form has Folder Name, Share Folder, Workspace Access Settings; nested sub-folders; Pin to top; drag and drop; folder tree in a side list with "See more ({count})". Empty state: "You have no folders · Start by creating a new folder…".
- **Card / right-click menu:** Open Editor, Go to Video, Open share page, Rename, Move, Share, Collaborators, Download / Download Audio, Change Thumbnail, Edit as New, Translate as New, Create Template, Open Containing Folder, Trash.
- **Bulk:** checkbox at thumbnail top-left, Select All, bulk move and download (folder download as .zip with resolution choice).
- **Privacy levels:** Private / Shared to specific people / Public (workspace).
- **Search:** "Search by title, script, or avatar…"; sort Best match / Newest first.
- **Collections:** auto-created folders for batch translations and batch videos, with per-item status.
- https://help.heygen.com/en/articles/13016632-how-to-organize-your-workspace-folders-collections-more
- REPORTED: "all projects library with folders, search, sort and video thumbnails" (saasui).

**Video share page** (`/share`, `/videos/…`):
- Player with emoji reactions and timestamped comments. Comments tab ("Comment at {time}", Reply, "No comments yet"), Transcript.
- Tabs Edit / Insights / Translate.
- Insights ("Engagement Insights"): views, shares and downloads, average watch time, completion rate, total watch time.
- Captions section: Turn on captions, Edit Captions, Publish Captions, Upload .srt.
- "Customize Your Video Share Page": title, description, CTA button (label, URL, colour style), Logo, Video Cover, Background, Theme Light / Dark, Hide HeyGen Button.
- Share dialog:
  - "Enable Sharing" toggle; audience: your team, anyone with the link, or a project folder.
  - Require Password (Enterprise).
  - Tiles: Copy link, Email, X, LinkedIn, Facebook, Instagram, Message; embed and GIF thumbnail.
- Download: resolution; video / captions only / audio only; "Advance Settings" 720p / 1080p / 4K; Export as SCORM / xAPI.
- Video approval: Request Approval → reviewers → Approve / Request Changes.
- "⋯" menu: Edit in AI Studio, Edit as new, Create Template, Move to, Feedback, Copy Video ID, Trash.
- Sources: https://help.heygen.com/en/articles/11788079-how-to-share-your-videos; https://help.heygen.com/en/articles/9834825-how-to-download-or-export-a-video; S1 `VideoSharePage`, `Video`.

### 2.9 Video Translate (`/apps/translate`, `/video-translation`, `/video-translation/proofread`)

- **Landing:** title "Translate your videos in 175+ languages"; dropzone "Drop your videos here to translate"; "Browse local files"; "Select an existing project"; URL field. REPORTED: "drag-and-drop upload for 175+ languages with YouTube/Drive URL option" (saasui).
- **Setup:** "Source video language" (Auto-detect) → "Translate it into" (up to 10 languages, each with Base or Localized accent variants).
- **Engine picker:** Audio only (4 credits/min) / Speed (6) / Precision (10, "2x cost" badge).
- **Extras:** Trim Video; "Add source transcript" (SRT).
- **Advanced settings modal:** Brand glossary; "Adjust video length to fit speech" (Dynamic Duration ±20%); Create a Collection; Keep original music / Remove background sound; "Keep source quality and format"; Enable Captions; "Enhance translated voice".
- **Button:** "Translate". Email on completion. Batch Dubbing ("Add {count} to Batch").
- https://help.heygen.com/en/articles/10029081-how-to-get-started-with-video-translation
- **Proofread editor:**
  - Preview / Result tabs above the video; Result shows "Version X" and "Stale" badges.
  - Segment list with a speaker column (including Off-Screen) and editable translated text; "Add a segment below"; per-segment Play.
  - Pronunciation on highlighted words.
  - Track voice menu: Select track voices / Create voice clone.
  - Find and replace across Original / Translation.
  - "Ask AI alongside your work" chat ("Ask about translations…").
  - Versions list with restore; "Add language".
  - "Generate result" with options Include captions / audio only.
  - Invite proofreaders (Enterprise); "Submit proofread for review"; Excel / SRT import and export.
  - https://help.heygen.com/en/articles/10024431-how-to-use-proofreading-for-video-translation

### 2.10 Video Agent (`/video-agent`, `/video-agent/projects`, `/video-agent/assets`, `/agent`)

- **Composer:** prompt box with "+" (Brand System, attachments) and an Avatar Picker above the chat (Recently Used / My Avatars).
- **Options:** Chat Mode vs Autopilot Mode; Duration; Orientation (Landscape / Portrait); Seedance toggle; Incognito Mode; Script field and Instructions field; 100+ Styles (Mar 2026).
- **Flow:** "Generate your Video Plan" (free to iterate) → reply with feedback or type "Proceed" → a confirmation card shows the estimated credits → waiting room.
- **Waiting room** (S1): stages Creating assets → Placing scenes → Ordering scenes → Generating video, "{progress}% ready", per-asset lines such as "Pulling stock media — '{name}'". An education carousel runs alongside: "While your video renders".
- **After generation:** chat edits; scene-level "Edit" + prompt; "Edit a Copy in AI Studio"; "Adjust script & avatar" panel (Choose model, Rendering quality 720p / 1080p / 2K, Voice Delivery).
- **Credits:** about 60–80 per minute standard; about 180–240 with Seedance.
- Sources: https://help.heygen.com/en/articles/12402907-how-to-get-started-with-video-agent; https://help.heygen.com/en/articles/16007192-video-agent-faq; https://www.heygen.com/blog/heygen-july-2026-release (HyperFrames motion graphics, storyboard approval).
- Mobile web is blocked: "Video Agent Isn't Available on Mobile".

### 2.11 Apps (`/apps`, `/apps/integrations`, `/apps/all-outputs`)

**App Library** (S1): title "App Library · Use HeyGen Apps to up-level your creative process". Three sections headed "Apps to create avatars, videos, images and more.", "Apps to enhance all that you create.", "Apps to edit, change, and remix your content". Hero cards for Video Agent, Cinematic Shots, Creative Studio, Video Translate. Each app card has a preview image or video, a pastel-backed icon, name, one-line description, and "NEW" where relevant; "Try {name}". REPORTED: "featured apps carousel and categorized grid of HeyGen tools" (saasui).

**Registry** (S4 app registry + S1 names, with routes):
- AI Studio; Video Agent; Creative Studio (`/apps/creative-studio`, tabs Video / Image / Voice); Cinematic Shots / Avatar Shots.
- Video Podcast (`/apps/video-podcast-v2`); Translate Videos; AI Clipping (`/apps/instant-highlights`); Batch Mode; Product Placement.
- Face Swap; Generate AI Video; Generate Images; Upscale Video / Upscale Images and Videos; Speech Cleanup (`/apps/filler-word-removal`).
- PPT/PDF to Video; Interactive Video; LiveAvatar; AI Business Card (flagged).
- Flagged or internal-looking: Multi-Avatar, Segment Edit, Perfect Take, Pharma Studio, Leadmaxx.
- Also "Automated Video Series" under Apps → Automated.

**Individual apps** (all CONFIRMED from help):
- **Creative Studio.** Composer with model picker at top-right (grouped Frontier / More models, credit rate per row). "Describe your shot" box with Script Enhance; "Add" (avatar, start frame, references); bottom pills for length, resolution, aspect; credit estimate → Generate. Inspiration tiles. Results in a creations area below. Failed cards offer Re-edit / Copy prompt / Copy ID / Delete. https://help.heygen.com/en/articles/17680953-how-to-create-b-roll-with-heygen-creative-studio
- **Video Podcast.** Host and Guest slots with a swap icon; per-speaker voice; "Invite a guest" by email; topic or "Use my own script" toggle; Layout 16:9 or 9:16; Length 1 / 2 / 3 min; Resolution. "Generate Preview" in the right panel with a credit estimate → Script panel and Details panel → "Create Podcast". https://help.heygen.com/en/articles/15707329-how-to-use-heygen-video-podcast
- **AI Clipping.** URL or upload → Clip Duration, Aspect Ratio (16:9 / 9:16 / 1:1), Caption Settings, Additional instructions, "Surprise me". Result page: right panel tabs Actions / Transcript / Score (Hook, Flow, Value, Trend); "All clips from…" below the player. https://help.heygen.com/en/articles/9278954-ai-clipping-explained
- **PPT/PDF to Video.** "Upload your presentation" or "Generate a new presentation"; avatar as a circular bottom-right overlay; "Use speaker notes as script"; "Import slide content as editable elements"; "Save brand". https://help.heygen.com/en/articles/13007313-ppt-pdf-to-video
- **Batch Mode.** Project name, aspect ratio, stacked script boxes ("+"), avatars and voice per box, "Generate Videos". https://help.heygen.com/en/articles/12704317-batch-mode
- **Product Placement.** Product image + avatar → "Generate Combined Images" (four options) → "Next: Add a script" → script or audio, voice, custom motion, 720p / 1080p → "Generate Video". https://help.heygen.com/en/articles/12704854-product-placement-combine-a-product-with-an-avatar-in-a-video
- **Quick Avatar Video.** My / Public avatars, orientation, "Add Script", voice, engine, resolution → "Generate Video" or "Edit in Studio". https://help.heygen.com/en/articles/12903996-quick-avatar-video
- **Automated Video Series.** Shortcut Name, Prompt with suggestions, Avatar, Schedule → "Save Automation" / "Publish Automation". https://help.heygen.com/en/articles/13006248-automated-video-series
- **Upscale Video.** Standard / Precise engines, to 4K, frame interpolation. https://www.heygen.com/blog/heygen-march-2026-release

**Integrations page.** REPORTED: "connector cards for ChatGPT, n8n, Slack, HubSpot, Canva and more" (saasui). Release notes add Claude, Gamma, Granola, Superhuman, Lovable, LinkedIn, Stripe, Adobe Express.

### 2.12 Interactive Avatar / LiveAvatar

LiveAvatar is a separate product at app.liveavatar.com, using the HeyGen login. Interactive Avatar was the beta inside HeyGen Labs; inside HeyGen it now shows as an app card with a "Try LiveAvatar" modal.

- **Dashboard tabs:** My Avatars / Public Avatars / Examples.
- **Left menu:** Playground → Voice Agents → "Create New" → "Build from scratch" → name → "Configure the brain" (context, text only; formerly called knowledge base) → "Configure the voice" (voice and default language) → Save.
- **Then:** Avatars → open an avatar → "Select voice agent" dropdown at the bottom → "Chat Now".
- **Share:** Share button, hosted link, HTML embed.
- Sources: https://help.heygen.com/en/articles/10035615-how-to-get-started-with-liveavatar; https://help.heygen.com/en/articles/12758516-introducing-liveavatar; custom avatar footage rules at https://help.heygen.com/en/articles/9612935-liveavatar-custom-liveavatar-creation-guide
- HeyGen-side remnants in S1/S4: routes `/interactive-avatar`, `/streaming-embed`; a "Knowledge Base" page ("Upload documents and data sources for your AI avatars to reference").

### 2.13 Settings (`/settings`), team, billing, API

- **Open:** account avatar at bottom-left → Settings.
- **Settings sidebar** (S1 `Settings.sidebar_*`; grouping partly INFERRED; several are Enterprise-only):
  - Personal Settings: Account, Preferences, Personalization.
  - Workspace / Organization: General, Members, Sub-Workspaces, Access & Invitations, Content Permissions, Export Settings, Billing / Plan & Billing, Usage / Usage & History, History, Connections, Data Connections, Shared avatars, API, Agentic Skills, Security, AI Governance, Brand Governance, Encryption, Audit Logs, Admin Control Portal, Get help.
- **Account:** photo (crop), name, email (Change Email), password, 2-factor authentication, Delete Account. REPORTED matching screenshot (saasui).
- **Preferences:** Appearance Light / Dark / Auto; Language (21 locales); Use cases.
- **Personalization:** tabs Memory / Brand System / Brand Glossary; memory items with Name and "Use when"; filters All / Approved / Pending. https://help.heygen.com/en/articles/15046858-heygen-s-preferences-personalization-settings
- **Plan & Billing:** current plan, "Upgrade" (plan picker with Monthly / Yearly toggle), "Manage Billing" (Stripe), "Buy / Manage Add Ons", auto-reload credits, promo code.
  - REPORTED: "plan picker modal comparing Free, Creator and Pro tiers with yearly billing toggle" (saasui).
  - https://help.heygen.com/en/articles/8300824-how-to-upgrade-or-downgrade-your-subscription
- **Usage & History:** Usage Overview meters, with tabs Features / Members; History table with credits per generation and tabs All Actions / API Usage / Audit Log and others. REPORTED: "usage meters for avatars, looks and motion plus credit history table" (saasui).
- **Members** ("Members & Workspaces"): member table (Name, Role, Status), filter All Workspaces, active / pending, export.
  - Invite modal: by email / by link, with an On / Off toggle for the link.
  - Roles: Super Admin ("Can remove content and purchase"), Creator ("Can create content and use the API"), Viewer ("Can view content").
  - "Manage Seats"; "${price}/seat".
  - Sub-Workspaces tab: Create / Edit Sub-Workspace.
- **Security:** Authentication Methods (Google, Apple, Magic Link, Email + Password, SAML SSO), 2FA enforcement, Domain registration (TXT record), SAML group mapping, SCIM.
- **General (Enterprise Workspace Settings):** Access & Invitations, Video Distribution (download / public publishing / social sharing), Feature Settings, Avatar Controls, AI Governance, Video Approval, Default Project Access, Danger zone (Delete workspace). https://help.heygen.com/en/articles/14172266-advanced-enterprise-settings
- **Connections:** YouTube, LinkedIn.
- **API / Developers** (`/developers/api`): API Keys table with scoped permissions and expiration; Balance, Add funds, Auto-reload, Invoice history; Usage; Models; Webhooks (endpoint, signing secret, verify).

### 2.14 Trash (`/projects/trash`, `/trash`)

- **Location:** "Trash" option on the left of the Projects page. https://help.heygen.com/en/articles/8300959-how-to-restore-a-deleted-video
- **Strings** (S1 `Trash`): title "Recently Deleted"; per-item Restore and "Delete Forever"; "Delete All" with confirmation "This action cannot be undone. All {count} items will be permanently deleted."; "Load More ({count} remaining)".
- **Empty state:** "No deleted videos found".

### 2.15 Help and learning

- In-app Academy at `/academy` ("From HeyGen Academy", lessons with "Features Covered").
- Help Center, "Learning & Community" and "Resources" links in the account menu.
- Orby assistant (chat, updates, support).
- Bell → "What's new".
- "Tutorials" in the editor hamburger menu.

---

## 3. Visual design

All tokens below are CONFIRMED from S3 unless marked otherwise.

### 3.1 Typography

- **UI font:** `"TT Norms Pro"`, preloaded as Medium.
- **Display / headline font:** `ABC Solar Display` (weight 600) and `ABC Solar Display Headline` (Bold).
- **Fallbacks:** the shell stylesheet also declares `SF Pro Display` in weights 100–900; system stack otherwise.
- **Scale:**
  - Title: 12/14, 14/18, 16/20, 18/22, 20/24 at weight 700; 32/36 at weight 800.
  - Body: 12/16, 14/20, 16/24 at weight 400.
  - Label: 12/16 at 400; 14/20 and 16/24 at 600.
  - Display: 24, 30, 36, 48, 60, 72px, with -0.02em tracking from 36px up.
  - Named weights include a custom "normal" at 450.
  - Rail labels are 11px/16px semibold (S4).

### 3.2 Colour

- **Brand:** HeyGen Blue `#00c4ff`, with a 10-step ramp from `#e6f9ff` to `#005873`; accessible variant `#00a7d9`.
- **Secondary accents:** green `#35c838` / `#00bf8f`; "AvatarPink" `#f3a6ff`; "AgentCyan" `#04d3d6`; violet `#7559ff`; navy `#1f6aff`; gold `#ffaa00`; orange `#ff791a`; red `#e54945`.
- **Signature gradients:**
  - Home pill: `linear-gradient(127deg, rgb(243,166,255) 12%, rgb(0,196,255) 70%, rgb(53,200,56) 89%)` (pink → cyan → green).
  - Prism: purple `#c259ff` → pink `#ff5993` → blue `#00a1f2` → violet `#7559ff`.
  - Avatar V: `#7a77ff` → `#e68cff` → `#f3a6ff`.
  - Active Home label: `linear-gradient(145deg, #00c4ff 12%, #35c838 89%)`.

| Token | Light | Dark |
|---|---|---|
| Main surface (`fillGeneral`) | `#ffffff` | `#16171a` |
| Block / background | `#f7f8fa` | `#1f2124` block, `#0d0e0f` background |
| Raised (`fillUpper`) | `#ffffff` | `#252629` |
| Title text | `#232833` | white 90% |
| Body text | `#4e5666` | white 75% |
| Support text | `#687080` | white 50% |
| Disabled text | `#bcc1cc` | white 25% |
| Line | `#e2e3e6` (darker `#cdced2`) | `#252627` |
| Hover | `#eaecee` | `#202122` |
| Selected | `#e2e3e6` | `#252627` |
| Primary-selected | `#e3f4fa` | `#0a3a49` |
| Tooltip | `#191919` | `#e7e7e7` |
| Primary button | bg `#19191a`, text white, hover `#4e5666` | bg `#00c4ff`, text `#00141a`, hover `#00a7d9` |

- Theme is set by `data-theme` on `<html>`, with modes Light / Dark / Auto.
- A separate warm theme is used for the first-party login and HyperFrames OAuth screens: background `#f2f0ed` (dark `#201e1b`), green brand `#37de91`.

### 3.3 Shape, elevation, density, motion

- **Radii:** 8 / 12 / 16 / 20px; buttons fully rounded (100px pill); rail icon tiles 12px; outer nav container 24px (S5).
- **Shadows:** elevated `0 2px 4px -2px rgba(0,0,0,.06), 0 4px 8px -2px rgba(0,0,0,.1)`; button glow `0 4px 12px rgba(117,89,255,.15)` in light and `rgba(0,196,255,.3)` in dark.
- **"Liquid glass"** (INFERRED mapping of S5 classes to the nav container): white at 80% (dark: black at 60%) with a hairline border of black 6% / white 8%. A `liquid_glass` module is loaded with the shell.
- **Density:** 14px base body; 40px control and pill heights; 32px icon buttons; 16–24px page gutters; content max-width 1440px.
- **Motion:** 150–300ms transitions, ease-out; hover scale 110% on rail icons; skeleton shimmer loading; brand-cyan 48px spinner; reduced-motion handled.
- **Custom cursors:** the app ships its own cursor image set (`/cursor2/*.png`).
- **Iconography:** an SVG sprite (`/sprite-*.svg`) of line-style icons at 16 / 24px. Rail icon names: `avatar-menu`, `magic`, `brand-kit`, `design`, `folder`, `code`, `video-sparkle`, `rocket`. Visual style (stroke weight, fill) is not verifiable from names.
- **App cards:** icon on one of six pastel backgrounds (`#E8F0FE`, `#FEF3E8`, `#E8FEF0`, `#F3E8FE`, `#FEE8F0`, `#E8FEFE`) with preview image or video (S4).

### 3.4 Editor arrangement

Described in 2.2: script panel left, canvas centre, tool tabs and Properties inspector right, scene-card timeline bottom, with a top bar holding name, hamburger, orientation, brand, save, invite, Preview and Generate. Left / centre / bottom are CONFIRMED by help and Academy. The right-side menu is CONFIRMED by help. The exact split between "tabs above the canvas" and "right menu" differs between sources: the Academy says Avatars and visuals tabs sit above the canvas; help says a right-side menu. The Nov 2025 redesign may explain the difference.

### 3.5 Home "create" hero

- Greeting line plus prompt composer or workflow cards, described in 2.1.
- A full-bleed home layout mode exists (`use_full_bleed_home_layout`), and a `HomeOrb` stylesheet suggests an animated orb visual. INFERRED: this is tied to Orby.

---

## 4. Things I could not verify

1. Which Home variant (lobby, v4 avatar-first, v2 prompt-first, verticals) a given account sees today. All are in the shipped strings; assignment is by experiment or flag.
2. The exact rendered order of the account-menu and Settings-sidebar items, and which are plan-gated. Labels are confirmed; order and grouping are partly inferred.
3. Whether a credits counter is permanently visible in the top bar, or only in the account menu and plan CTA.
4. The current contents and form of the Create button (single dropdown vs Home cards). The 24 entries are confirmed strings only.
5. Trash retention period. The help article does not state it.
6. Whether Vimeo URLs are accepted in Translate. Help says "Vimeo links are not currently supported"; the app placeholder says "Paste a Google Drive or Vimeo URL".
7. Whether Brand Systems has a "brand voice" field or intro/outro. I found neither.
8. Pixel-level layouts of Avatars, Voices, Projects, Templates and Settings (column counts, card aspect ratios, spacing). Only saasui captions and strings were available; I could not view the screenshots themselves.
9. Icon visual style, and the exact look of "liquid glass" surfaces.
10. The March 2026 "redesigned homepage" community post (communityone.io returned 403).
11. Where Studio Neo / Story editor, Explore, Grow, Workflows, Multi-Avatar, Segment Edit, Perfect Take and Leadmaxx are exposed; several look flagged or internal.
12. The LiveAvatar builder beyond the help text (embed dialog, persona fields). It is a separate app I did not inspect.
13. Empty states for pages other than those quoted above.
14. Mobile web and native app IA were not covered.

## Sources

- HeyGen app (official, public): https://app.heygen.com/home · https://app.heygen.com/login · https://app.heygen.com/locales/en-US.json · https://app.heygen.com/main-BF95IqJp.css · https://app.heygen.com/main.app-Cm0VXWER.js · https://app.heygen.com/home_layout-D6cFwp0e.js
- Help centre: https://help.heygen.com/en/ plus the article URLs cited inline
- Release blog: https://www.heygen.com/blog/heygen-november-2025-release · https://www.heygen.com/blog/heygen-december-2025-release · https://www.heygen.com/blog/heygen-february-2026-release · https://www.heygen.com/blog/heygen-march-2026-release · https://www.heygen.com/blog/heygen-april-2026-release · https://www.heygen.com/blog/heygen-may-2026-release · https://www.heygen.com/blog/heygen-june-2026-release · https://www.heygen.com/blog/heygen-july-2026-release · https://www.heygen.com/blog/heygen-august-2026-release · https://www.heygen.com/blog/heygen-september-2026-release · https://www.heygen.com/blog/heygen-october-2026-release
- Academy: https://www.heygen.com/academy/ai-studio/how-to-create-a-new-project
- Third party: https://www.saasui.design/application/heygen · https://releasebot.io/updates/heygen
