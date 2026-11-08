"""v0.686 DUNIYA BHAR KE TEMPLATE: the world catalogue behind the Web Studio's 1,00,000 templates.

50 sectors of the world economy x 20 subjects each = 1,000 subjects, from local shops to SaaS, universities,
hospitals, studios, climate tech and public services; x 10 website types (landing page, company site, online store,
booking, portfolio, magazine, community, event, web app, marketplace) x 10 design styles = 100,000.

Every sector names the website library card (`field`) the builder uses for it, so a template can always be built;
the subject's own words travel in the prompt. Data only - nothing here calls a model.
"""
from __future__ import annotations

# (key, label, library field the builder uses, who visits, trust signals, rules line)
SECTORS: list[tuple[str, str, str, str, str, str]] = [
    ("saas", "Software & SaaS", "saas_product", "teams evaluating a tool, buyers comparing plans",
     "customer logos she approves, uptime, security page, real reviews", "Price, uptime and security claims only as she gives them; GDPR / DPDP privacy page."),
    ("ai", "AI & data", "ai_startup", "product teams, developers and buyers of AI tools",
     "model cards, benchmarks she can cite, data handling page", "No claims of accuracy or 'human-level' without her source; say clearly what the AI does with user data."),
    ("devtools", "Developer tools & APIs", "software_company", "developers who want to try it in minutes",
     "GitHub stars, docs quality, status page, changelog", "Licence and pricing exactly as she states; code samples must run."),
    ("security", "Cybersecurity", "cyber_security", "CISOs, IT heads and small-business owners",
     "certifications she holds, incident response time, case studies", "No fear-selling or invented breach numbers; certifications only as held."),
    ("enterprise", "Enterprise & B2B services", "it_services", "procurement teams and decision makers",
     "client logos she approves, certifications, case studies with numbers she gives", "No guaranteed-ROI claims; case-study figures only from her."),
    ("consulting", "Consulting & professional services", "consultant_profile", "founders and managers looking for expert help",
     "credentials, years of practice, client results she shares", "Credentials exactly as held; no promised outcomes."),
    ("finance", "Finance & accounting", "chartered_accountant", "individuals and companies needing money advice",
     "registrations and licence numbers she gives, years of practice", "Regulated advice: registration numbers shown, no assured-return claims, risk lines where needed."),
    ("fintech", "Fintech & payments", "saas_product", "businesses and people managing money online",
     "regulatory status she holds, security practices, partner banks she names", "Only the licences she really holds; no 'zero risk'; fees shown as she sets them."),
    ("insurance", "Insurance", "insurance_agent", "families and businesses comparing cover",
     "licence number, claim support process, years serving", "Licence shown; no 'guaranteed claim' wording; product terms from the insurer only."),
    ("realestate", "Real estate & property", "builder_developer", "home buyers, renters and investors",
     "registration numbers (RERA where it applies), delivered projects, site photos", "Project registration shown; prices and possession dates only as she gives them."),
    ("architecture", "Architecture & interiors", "architect", "home owners and companies planning a space",
     "council registration, finished projects, awards she has", "Title and registration as held; project photos hers or credited."),
    ("construction", "Construction & engineering", "civil_contractor", "developers, owners and public tenders",
     "licences, safety record she gives, completed works", "No safety or completion guarantees beyond her contracts."),
    ("manufacturing", "Manufacturing & industrial", "factory", "procurement and engineering buyers",
     "certifications (ISO etc.) she holds, capacity, clients she approves", "Specs and certifications exactly as held; enquiries, not instant prices, unless she sets them."),
    ("energy", "Energy, solar & climate", "electrical_contractor", "homes, farms and companies cutting energy bills",
     "installations done, warranties she offers, certifications", "Savings shown only as her own worked examples, never as a promise."),
    ("auto", "Automotive & mobility", "car_dealer", "drivers buying, servicing or renting vehicles",
     "brand authorisation she holds, service record, reviews", "Prices, offers and EMI only as she gives them, with their terms."),
    ("logistics", "Logistics & supply chain", "freight_forwarder", "shippers and businesses moving goods",
     "fleet / network size she gives, licences, tracking", "No delivery-time guarantees beyond her terms."),
    ("travel", "Travel & tourism", "tour_operator", "travellers planning trips",
     "registrations, real traveller reviews, itineraries", "Package prices and inclusions exactly as she gives them; cancellation terms visible."),
    ("hospitality", "Hotels & stays", "boutique_hotel", "guests choosing where to stay",
     "real photos, guest ratings she links, location", "Room rates and amenities as she gives them; no fake 'only 1 room left'."),
    ("food", "Restaurants & cafes", "restaurant", "diners nearby and food lovers",
     "food licence number, real photos, reviews she links", "Food licence shown; veg / non-veg marks; no health-cure claims."),
    ("foodbrand", "Food & beverage brands", "snacks_brand", "shoppers and retail buyers",
     "food licence, ingredients, where to buy", "Ingredient and nutrition claims exactly as on her label."),
    ("retail", "Retail & shops", "general_store", "local shoppers and online buyers",
     "years in business, delivery area, return policy", "Prices only as she gives them; return and refund policy page."),
    ("fashion", "Fashion & apparel", "boutique", "shoppers who care about style and fit",
     "fabric and size details, return policy, real customer photos she approves", "Fabric and origin claims as true; size guide; return policy."),
    ("beauty", "Beauty & personal care", "skin_care_studio", "people booking or buying beauty care",
     "certified staff, hygiene practices, before / after only with consent", "No medical claims; before / after photos only with consent."),
    ("health", "Hospitals & clinics", "hospital", "patients and families",
     "doctors' registrations, departments, accreditation she holds", "Medical-ethics rules: factual information only, no 'best doctor', no cure claims."),
    ("wellness", "Fitness & wellness", "gym", "people starting or keeping a routine",
     "trainer certifications, facility photos, member stories with consent", "No weight-loss guarantees or medical claims."),
    ("pharma", "Pharma & medical devices", "pharma_wholesale", "doctors, hospitals and distributors",
     "licences, approvals she holds, quality certifications", "No promotion of prescription medicines to the public; approvals exactly as held."),
    ("school", "Schools", "cbse_school", "parents choosing a school",
     "affiliation number, results she gives, campus photos", "Affiliation shown; results only as she gives them; child photos only with consent."),
    ("university", "Colleges & universities", "degree_college", "students, parents and researchers",
     "approvals and accreditations held, faculty, placements she reports", "Approvals exactly as held; placement numbers only from her records."),
    ("edtech", "Online learning & coaching", "online_tutor", "learners and parents comparing courses",
     "teacher credentials, sample lessons, real results she gives", "No guaranteed-rank or job claims."),
    ("research", "Science & research", "education_ngo", "researchers, funders and the public",
     "publications, partners she names, funding sources", "Findings stated as published; data and image credits."),
    ("media", "Media & publishing", "writer", "readers and advertisers",
     "editorial policy, authors, sources", "Corrections policy; ads marked as ads; credits for images."),
    ("creative", "Design & creative studios", "graphic_designer", "brands looking for creative work",
     "portfolio she owns, clients she approves", "Only her own or credited work in the portfolio."),
    ("photo", "Photography & film", "photographer", "couples, brands and families booking a shoot",
     "portfolio, packages, reviews she links", "Only her own photos; client consent for people in them."),
    ("music", "Music & performing arts", "musician", "fans, venues and event planners",
     "shows played, releases, press she has", "Music and video rights hers or licensed."),
    ("gaming", "Gaming & esports", "software_company", "players and communities",
     "platforms, ratings, community size she gives", "Age rating shown; no real-money prizes unless legally run; no loot-box dark patterns."),
    ("events", "Events & weddings", "event_management", "couples and companies planning an event",
     "past events, vendors, reviews she links", "Package prices as she gives them; photos hers or credited."),
    ("sports", "Sports clubs & academies", "sports_complex", "players, parents and members",
     "coach certifications, results, facilities", "Child safety policy where kids train; results as she reports."),
    ("ngo", "Non-profits & causes", "ngo", "donors, volunteers and the people helped",
     "registration numbers, audited reports, impact numbers she gives", "Registration and tax-benefit status exactly as held; impact numbers only from her reports."),
    ("civic", "Public services & civic", "residents_association", "residents and citizens",
     "office-bearers, notices, meeting minutes", "Never look like an official government site; contact details real; plain language."),
    ("faith", "Faith & spiritual", "temple", "devotees and visitors",
     "trust registration, timings, events", "Respectful words; donations through her own account only; no miracle claims."),
    ("legal", "Law firms & legal services", "law_firm", "people and companies needing legal help",
     "enrolment details, practice areas", "Bar-council style rules: information only, no soliciting, a disclaimer page."),
    ("hr", "HR, recruitment & staffing", "placement_agency", "job seekers and employers",
     "licence where needed, placed candidates she reports, employer clients", "Never charge job seekers where the law forbids; jobs only real openings."),
    ("agri", "Agriculture & food tech", "organic_farm", "buyers, farmers and food companies",
     "certifications (organic etc.) held, farm photos, origin", "Organic or origin claims only with her certificate."),
    ("pets", "Pets & veterinary", "veterinary_hospital", "pet parents",
     "vet registrations, facility photos, reviews", "No cure claims; adoption and breeding as the law allows."),
    ("kids", "Kids & family", "daycare", "parents of young children",
     "staff checks, safety measures, licences", "Child photos only with consent; safety policy visible."),
    ("home", "Home services", "cleaning", "home owners needing help fast",
     "verified staff, service area, guarantees she offers", "Prices and guarantees exactly as she sets them."),
    ("telecom", "Internet & telecom", "isp", "homes and offices choosing a connection",
     "coverage area, plans, support hours", "Speeds as 'up to' with her fair-use terms; licence shown."),
    ("crafts", "Crafts & handmade", "handicrafts", "gift buyers and collectors",
     "maker story, materials, shipping", "Handmade and material claims as true; shipping and return policy."),
    ("personal", "Personal brands & creators", "content_creator", "followers, brands and clients",
     "work samples, collaborations she approves", "Sponsored content marked; only her own work."),
    ("community", "Communities & clubs", "alumni_association", "members and people who want to join",
     "office-bearers, events, member count she gives", "Member data private; joining rules clear."),
]

# 20 subjects per sector, in the same order as SECTORS (a subject reads after 'for a' / 'for an').
SUBJECTS: dict[str, list[str]] = {
    "saas": ["project management tool", "CRM for small teams", "HR and payroll platform", "invoicing app", "help-desk software",
             "email marketing platform", "scheduling app", "inventory management system", "e-signature service", "survey builder",
             "website analytics tool", "password manager", "team chat app", "learning management system", "field service app",
             "subscription billing platform", "no-code app builder", "restaurant POS software", "clinic management software", "school ERP"],
    "ai": ["AI writing assistant", "AI customer-support agent", "computer-vision startup", "voice AI platform", "AI tutor app",
           "data-labelling company", "machine-learning consultancy", "AI image generator", "document-AI product", "AI sales assistant",
           "recommendation engine", "AI translation service", "data analytics agency", "AI meeting notes tool", "predictive maintenance platform",
           "AI legal research tool", "AI hiring platform", "AI medical-imaging startup", "chatbot builder", "data warehouse consultancy"],
    "devtools": ["payments API", "maps API", "open-source database", "CI/CD platform", "code review tool", "feature-flag service",
                 "error monitoring tool", "API testing tool", "headless CMS", "authentication service", "cloud hosting provider",
                 "low-code backend", "logging platform", "SMS and OTP API", "search API", "web scraping API", "mobile SDK",
                 "infrastructure-as-code tool", "developer bootcamp", "open-source UI library"],
    "security": ["penetration testing firm", "managed security service", "email security product", "endpoint protection company",
                 "security awareness training", "identity and access platform", "cloud security startup", "cyber insurance broker",
                 "digital forensics lab", "VAPT consultancy", "bug bounty platform", "firewall reseller", "data privacy consultancy",
                 "SOC-as-a-service", "secure file-sharing app", "CCTV and access control installer", "anti-fraud platform",
                 "compliance automation tool", "ethical hacking academy", "encryption software"],
    "enterprise": ["IT outsourcing company", "BPO and call centre", "ERP implementation partner", "facility management company",
                   "corporate training firm", "market research agency", "translation and localisation firm", "B2B lead-generation agency",
                   "packaging supplier", "corporate gifting company", "office furniture supplier", "data centre provider",
                   "managed print service", "industrial cleaning contractor", "corporate travel desk", "event technology vendor",
                   "procurement platform", "background verification agency", "document management company", "uniform supplier"],
    "consulting": ["management consultancy", "business coach", "startup advisor", "marketing strategist", "brand consultant",
                   "operations consultant", "sustainability consultant", "export consultant", "franchise consultant",
                   "retail consultant", "career counsellor", "leadership coach", "pricing consultant", "M&A advisory firm",
                   "public-relations consultant", "change management firm", "quality systems consultant", "supply-chain consultant",
                   "food-safety consultant", "real-estate advisor"],
    "finance": ["chartered accountancy firm", "tax filing service", "bookkeeping firm", "virtual CFO service", "audit firm",
                "company registration service", "GST consultancy", "payroll bureau", "wealth advisor", "financial planning practice",
                "investment research firm", "family office", "loan advisory firm", "valuation firm", "trust and estate planner",
                "startup fundraising advisor", "NRI tax service", "accounting software reseller", "credit repair advisor", "co-operative credit society"],
    "fintech": ["digital wallet", "UPI payments app", "neobank", "personal finance app", "expense management platform",
                "buy-now-pay-later service", "micro-lending platform", "invoice discounting platform", "crypto tax tool",
                "payment gateway", "remittance service", "robo-advisor", "stock-learning app", "insurance-tech startup",
                "credit score app", "payroll card provider", "merchant POS terminal company", "savings app for kids",
                "gold savings app", "accounting API"],
    "insurance": ["health insurance advisor", "motor insurance agency", "life insurance advisor", "term insurance comparison site",
                  "travel insurance seller", "business insurance broker", "crop insurance helper", "pet insurance agency",
                  "home insurance advisor", "claims assistance service", "group health broker", "marine insurance broker",
                  "cyber insurance advisor", "insurance training academy", "reinsurance broker", "micro-insurance provider",
                  "senior-citizen insurance advisor", "two-wheeler insurance agency", "liability insurance broker", "insurance surveyor"],
    "realestate": ["luxury apartment project", "villa community", "plotted development", "co-living brand", "student housing provider",
                   "commercial office tower", "property management company", "rental agency", "real-estate investment firm",
                   "vacation home rental", "retirement community", "warehouse leasing firm", "affordable housing project",
                   "home inspection service", "property valuation firm", "real-estate photography studio", "coworking space",
                   "shop leasing agency", "NRI property service", "real-estate brokerage"],
    "architecture": ["architecture studio", "interior design firm", "landscape architect", "kitchen design studio", "lighting designer",
                     "furniture design studio", "sustainable architecture practice", "office interiors company", "home renovation firm",
                     "3D visualisation studio", "modular kitchen brand", "wardrobe maker", "smart-home installer", "heritage restoration architect",
                     "retail store designer", "hospitality interior studio", "urban planning firm", "acoustic consultant", "vastu consultant", "tile and stone showroom"],
    "construction": ["civil contractor", "road construction company", "pre-engineered building maker", "waterproofing specialist",
                     "structural engineering firm", "MEP contractor", "fabrication workshop", "scaffolding rental", "demolition contractor",
                     "concrete supplier", "elevator installer", "fire-safety contractor", "solar EPC contractor", "plumbing contractor",
                     "electrical contractor", "painting contractor", "steel structure company", "pool construction company",
                     "construction equipment rental", "building materials store"],
    "manufacturing": ["precision engineering workshop", "plastic moulding company", "packaging manufacturer", "textile mill",
                      "garment exporter", "furniture factory", "chemical manufacturer", "food processing plant", "auto-parts maker",
                      "electrical panel manufacturer", "pump manufacturer", "machine tool builder", "3D printing service",
                      "CNC machining shop", "paper products maker", "glass manufacturer", "rubber products company",
                      "ceramics factory", "industrial valve maker", "LED lighting manufacturer"],
    "energy": ["rooftop solar installer", "EV charging network", "battery storage company", "wind energy developer",
               "energy audit firm", "biogas plant builder", "solar pump supplier", "green hydrogen startup", "carbon accounting tool",
               "energy-efficient lighting brand", "inverter and UPS dealer", "smart meter company", "climate-tech startup",
               "waste-to-energy company", "recycling company", "water treatment company", "rainwater harvesting installer",
               "sustainable packaging brand", "electric scooter maker", "home energy app"],
    "auto": ["car dealership", "used-car marketplace", "bike service centre", "car rental company", "EV showroom",
             "car detailing studio", "tyre and alignment shop", "auto-parts store", "driving school", "car wash chain",
             "vintage car restorer", "fleet management company", "self-drive bike rental", "truck dealership",
             "car accessories brand", "auto insurance helper", "motorcycle customiser", "roadside assistance service",
             "car subscription service", "tractor dealer"],
    "logistics": ["courier company", "freight forwarder", "warehouse provider", "cold-chain company", "packers and movers",
                  "last-mile delivery startup", "trucking company", "customs broker", "shipping line agent", "air cargo agent",
                  "e-commerce fulfilment centre", "fleet tracking provider", "logistics marketplace", "bike delivery service",
                  "pallet and crate supplier", "port services company", "rail freight agent", "relocation service",
                  "supply-chain software", "intercity transport service"],
    "travel": ["adventure tour company", "luxury travel agency", "pilgrimage tour operator", "honeymoon planner", "trekking company",
               "visa service", "student travel agency", "corporate travel agency", "cruise booking agent", "wildlife safari company",
               "city walking tours", "travel blog", "bus booking service", "cab service", "heli-tour operator",
               "camping and glamping site", "houseboat operator", "desert safari company", "ski and snow tours", "backpacker travel club"],
    "hospitality": ["boutique hotel", "beach resort", "homestay", "business hotel", "hostel", "heritage palace hotel",
                    "farm stay", "serviced apartments", "wellness retreat", "banquet and wedding venue", "conference centre",
                    "eco lodge", "hill-station cottage", "airport hotel", "glamping camp", "spa resort", "budget hotel chain",
                    "lake-view villa", "jungle resort", "rooftop lounge"],
    "food": ["fine-dining restaurant", "family restaurant", "cafe", "cloud kitchen", "bakery cafe", "pizzeria", "street-food stall",
             "vegan restaurant", "sweet shop", "ice-cream parlour", "food truck", "brewery and bar", "tea room", "juice bar",
             "thali restaurant", "sushi bar", "biryani house", "dessert studio", "catering company", "tiffin service"],
    "foodbrand": ["organic snacks brand", "coffee roaster", "tea brand", "spice brand", "craft chocolate maker", "healthy cereal brand",
                  "pickle brand", "plant-based milk brand", "protein bar brand", "honey brand", "packaged water company",
                  "frozen foods brand", "baby food brand", "pet food brand", "artisanal cheese maker", "sauce and condiment brand",
                  "energy drink brand", "millet foods brand", "ghee brand", "dry fruits brand"],
    "retail": ["supermarket", "electronics store", "mobile phone shop", "bookstore", "toy store", "gift shop", "furniture showroom",
               "hardware store", "stationery shop", "optical store", "pharmacy", "home decor store", "sports goods store",
               "kitchenware shop", "florist", "pet supplies store", "musical instruments shop", "watch store", "perfume shop", "convenience store"],
    "fashion": ["fashion label", "saree boutique", "menswear brand", "kids clothing brand", "sneaker store", "jewellery brand",
                "handbag brand", "bridal couture house", "sustainable fashion brand", "activewear brand", "eyewear brand",
                "lingerie brand", "ethnic wear store", "tailoring studio", "streetwear label", "watch brand", "leather goods maker",
                "fashion rental service", "thrift store", "plus-size fashion brand"],
    "beauty": ["hair salon", "skincare brand", "makeup artist", "nail studio", "men's grooming salon", "spa", "cosmetics brand",
               "bridal makeup studio", "beauty academy", "hair-care brand", "fragrance brand", "barbershop", "lash and brow studio",
               "ayurvedic beauty brand", "tattoo studio", "beauty subscription box", "mehendi artist", "wellness spa chain",
               "organic soap maker", "aesthetic clinic"],
    "health": ["multispeciality hospital", "dental clinic", "eye hospital", "fertility clinic", "physiotherapy centre",
               "diagnostic lab", "paediatric clinic", "dermatology clinic", "mental health practice", "orthopaedic clinic",
               "cardiology centre", "home-care nursing service", "telemedicine service", "maternity hospital", "cancer care centre",
               "ENT clinic", "ayurveda centre", "kidney care centre", "blood bank", "rehabilitation centre"],
    "wellness": ["gym", "yoga studio", "pilates studio", "CrossFit box", "martial arts academy", "meditation centre",
                 "personal trainer", "nutritionist", "dance fitness studio", "swimming school", "running club", "sports physio",
                 "weight-management programme", "senior fitness class", "boxing club", "cycling studio", "wellness coach",
                 "corporate wellness programme", "climbing gym", "online fitness programme"],
    "pharma": ["generic medicines maker", "medical device company", "surgical supplies distributor", "ayurvedic medicine company",
               "clinical research organisation", "diagnostic kit maker", "hospital equipment supplier", "pharmacy chain",
               "nutraceutical brand", "veterinary medicines company", "contract manufacturer", "lab equipment supplier",
               "orthopaedic implant maker", "dental supplies company", "home-care equipment rental", "biotech startup",
               "vaccine distributor", "herbal extracts exporter", "medical uniform maker", "health-tech hardware startup"],
    "school": ["preschool", "primary school", "international school", "boarding school", "CBSE school", "Montessori school",
               "special-needs school", "music conservatory for children", "art school", "language school", "STEM academy", "sports school",
               "homeschool co-op", "after-school programme", "early-learning centre", "junior college", "vocational school",
               "Waldorf school", "village school", "coding school for kids"],
    "university": ["engineering college", "medical college", "business school", "law school", "design institute",
                   "nursing college", "pharmacy college", "agricultural university", "research university", "liberal arts college",
                   "hotel management institute", "film school", "architecture college", "online university", "teacher training college",
                   "polytechnic", "aviation academy", "fashion institute", "media school", "skill university"],
    "edtech": ["exam coaching institute", "online tutoring platform", "spoken English course", "coding bootcamp", "UPSC coaching",
               "IELTS training centre", "abacus and maths classes", "music lessons app", "language learning app", "school tuition centre",
               "data science course", "design course", "CA coaching", "competitive exam test series", "kids' science kit brand",
               "professional certification provider", "career guidance platform", "online cohort course", "teacher marketplace", "study-abroad consultancy"],
    "research": ["research lab", "space-tech startup", "biotech research institute", "climate research centre", "museum",
                 "science centre", "observatory", "think tank", "archaeology project", "marine research station",
                 "agricultural research institute", "materials science lab", "public health research group", "open-data project",
                 "citizen science project", "robotics lab", "neuroscience lab", "linguistics research centre", "policy research institute", "innovation hub"],
    "media": ["news website", "magazine", "podcast", "YouTube channel", "local newspaper", "book publisher", "comics studio",
              "documentary studio", "radio station", "newsletter", "photo agency", "literary journal", "children's book publisher",
              "fact-checking organisation", "sports news site", "tech review site", "food blog", "travel magazine", "business news portal", "audio-book studio"],
    "creative": ["branding agency", "web design agency", "UI/UX studio", "animation studio", "illustration studio", "video production house",
                 "advertising agency", "social media agency", "content marketing agency", "motion design studio", "packaging design studio",
                 "type foundry", "printing press", "signage company", "3D modelling studio", "game art studio", "copywriting studio",
                 "influencer marketing agency", "AR/VR studio", "creative coworking space"],
    "photo": ["wedding photographer", "product photographer", "fashion photographer", "baby photographer", "drone videography service",
              "event videographer", "corporate film maker", "photo studio", "food photographer", "real-estate photographer",
              "pet photographer", "travel photographer", "documentary film maker", "music video director", "stock photo agency",
              "photo booth rental", "film editing studio", "photography school", "camera rental shop", "portrait artist"],
    "music": ["indie band", "music school", "recording studio", "classical singer", "DJ", "orchestra", "theatre company",
              "dance company", "music festival", "record label", "concert venue", "instrument maker", "music producer",
              "choir", "stand-up comedian", "magician", "folk music collective", "opera house", "sound engineering school", "karaoke bar"],
    "gaming": ["indie game studio", "mobile game", "esports team", "gaming cafe", "board-game cafe", "game publisher",
               "esports tournament", "gaming peripherals brand", "VR arcade", "game development school", "streaming creator",
               "game localisation studio", "game testing company", "fantasy sports platform", "puzzle game", "educational game",
               "gaming community", "retro games store", "escape room", "laser tag arena"],
    "events": ["wedding planner", "corporate event agency", "conference", "music concert", "trade exhibition", "birthday party planner",
               "destination wedding company", "event decorator", "event caterer", "tent and stage rental", "sound and light company",
               "event ticketing platform", "hackathon", "charity gala", "festival", "product launch event", "college fest",
               "marathon", "film festival", "book fair"],
    "sports": ["cricket academy", "football club", "badminton academy", "tennis club", "golf club", "swimming academy",
               "sports turf", "chess academy", "athletics club", "basketball league", "cycling club", "shooting academy",
               "kabaddi team", "hockey club", "sports complex", "yacht club", "equestrian centre", "skating rink",
               "table tennis club", "sports nutrition brand"],
    "ngo": ["education charity", "animal shelter", "environmental NGO", "women's empowerment foundation", "health charity",
            "disaster relief organisation", "old-age home", "children's home", "food bank", "clean-water project",
            "tree-planting campaign", "disability support group", "rural development trust", "scholarship foundation",
            "mental health helpline", "arts charity", "wildlife conservation trust", "blood donation drive", "skill-training NGO", "volunteer network"],
    "civic": ["residents' welfare association", "town library", "community centre", "public park trust", "neighbourhood watch",
              "co-operative housing society", "farmers' producer company", "self-help group", "traders' association",
              "municipal ward newsletter", "village panchayat information page", "civic issue tracker", "public transport users' group",
              "heritage walk society", "community radio", "local election awareness drive", "citizens' grievance forum",
              "public toilet map project", "community garden", "lost-and-found board"],
    "faith": ["temple", "church", "mosque committee", "gurudwara", "Buddhist monastery", "Jain temple", "meditation ashram",
              "yoga ashram", "spiritual teacher", "astrology practice", "pilgrimage trust", "religious school", "bhajan group",
              "prayer group", "charity kitchen", "spiritual retreat", "interfaith council", "festival committee",
              "devotional music label", "scripture study circle"],
    "legal": ["law firm", "corporate lawyer", "family lawyer", "criminal defence lawyer", "intellectual property firm",
              "immigration lawyer", "tax lawyer", "property lawyer", "notary service", "legal-tech startup", "arbitration centre",
              "labour law consultant", "consumer rights lawyer", "cyber law firm", "startup legal service", "trademark registration service",
              "divorce mediator", "legal aid clinic", "compliance law firm", "patent agent"],
    "hr": ["recruitment agency", "job board", "executive search firm", "staffing company", "campus hiring platform",
           "HR consultancy", "payroll outsourcing firm", "freelance marketplace", "internship platform", "background-check service",
           "gig-worker platform", "overseas job consultancy", "employee wellness provider", "training and skilling company",
           "remote hiring platform", "nurse placement agency", "IT staffing firm", "domestic help agency", "security guard agency", "career coaching service"],
    "agri": ["organic farm", "dairy farm", "fruit orchard", "plant nursery", "seed company", "fertiliser dealer", "farm equipment dealer",
             "agri-tech startup", "drip irrigation company", "fishery", "poultry farm", "farmers' market", "farm-to-table delivery",
             "mushroom farm", "vertical farm", "spice plantation", "beekeeping farm", "cattle feed company", "agri drone service", "flower farm"],
    "pets": ["veterinary clinic", "pet grooming salon", "pet boarding", "dog trainer", "pet shop", "pet food subscription",
             "cat cafe", "pet adoption centre", "aquarium store", "bird sanctuary", "pet portrait painter", "horse riding school",
             "pet insurance helper", "pet daycare", "pet accessories brand", "dog walking service", "pet transport service",
             "exotic pet vet", "animal rescue group", "pet bakery"],
    "kids": ["daycare", "play school", "kids' activity centre", "summer camp", "birthday party venue", "toy library",
             "baby store", "kids' clothing store", "children's theatre", "kids' coding class", "robotics club for kids",
             "kids' art studio", "children's dentist", "parenting blog", "children's portrait studio", "kids' book club",
             "trampoline park", "kids' yoga studio", "kids' tutoring centre", "family entertainment centre"],
    "home": ["home cleaning service", "plumber", "electrician", "pest control company", "AC repair service", "carpenter",
             "home painting service", "appliance repair service", "laundry service", "interior handyman", "water purifier service",
             "home security installer", "gardening service", "home shifting service", "maid agency", "sofa cleaning service",
             "roof repair company", "solar panel cleaning service", "home organiser", "smart-home setup service"],
    "telecom": ["fibre internet provider", "Wi-Fi hotspot network", "cable TV operator", "mobile phone repair chain", "telecom tower company",
                "IoT connectivity provider", "satellite internet reseller", "VoIP service", "leased-line provider", "data centre colocation",
                "network installation company", "IPTV service", "enterprise Wi-Fi integrator", "SIM card retailer", "telecom training institute",
                "CCTV-over-internet provider", "rural broadband co-op", "intercom installer", "OTT bundle seller", "network monitoring tool"],
    "crafts": ["handloom weaver", "pottery studio", "woodcraft workshop", "jewellery artisan", "handmade soap maker", "candle maker",
               "embroidery studio", "block-print studio", "bamboo craft collective", "leather craft workshop", "resin art studio",
               "macrame studio", "paper craft studio", "glass art studio", "metal craft workshop", "toy maker", "folk painting artist",
               "craft supplies store", "calligraphy studio", "upcycled goods brand"],
    "personal": ["personal portfolio", "freelance developer", "author", "public speaker", "life coach", "fitness influencer",
                 "travel creator", "food creator", "doctor's personal page", "researcher's homepage", "photographer's portfolio",
                 "artist's portfolio", "musician's page", "job-seeker resume", "startup founder", "politician's information page",
                 "chef", "teacher's page", "architect's portfolio", "designer's portfolio"],
    "community": ["alumni association", "professional association", "startup community", "book club", "hiking club", "photography club",
                  "coding meetup", "women in tech network", "parents' group", "senior citizens' club", "language exchange club",
                  "makerspace", "rotary-style service club", "fan club", "gardening club", "cycling community", "investor network",
                  "student society", "expat community", "volunteer club"],
}

# The 10 website types: (key, card noun, library goal, main action, pages, home sections in order, must-have features)
TYPES: list[tuple[str, str, str, str, str, str, str]] = [
    ("landing", "Landing page", "enquiry", "Get started / Book a call",
     "one long page + privacy",
     "hero with one promise, the problem, how it works in 3 steps, benefits, proof (only real), pricing or offer (her numbers), FAQ, final call to action",
     "one clear call to action repeated, a short lead form, fast first screen"),
    ("company", "Company website", "info", "Contact us",
     "home, about, services / products, work or case studies, team, careers, contact, privacy",
     "hero, what we do, who we serve, featured work, numbers she gives, team, testimonials (real), contact strip",
     "clear navigation, services pages, contact form, map and hours where it applies"),
    ("store", "Online store", "catalogue", "Add to cart / Order",
     "home, shop (categories), product page, cart and checkout, about, shipping and returns, contact, privacy, terms",
     "hero offer, featured categories, best sellers, why buy from us, reviews (real), newsletter",
     "product filters and search, cart, checkout through her own payment gateway, order tracking, returns policy"),
    ("booking", "Booking site", "booking", "Book now",
     "home, services with time and price, booking, about, FAQ, contact, privacy",
     "hero with 'Book now', services, how booking works, availability, team, FAQ, location",
     "real-time slots she confirms, booking reminders, cancellation policy"),
    ("portfolio", "Portfolio site", "portfolio", "Hire me / Start a project",
     "home, work (projects), project detail, about, services, contact",
     "big intro, selected work grid, approach, clients she approves, contact",
     "case-study pages with problem / process / result, fast image loading"),
    ("magazine", "Blog & magazine", "info", "Subscribe",
     "home, articles (categories), article page, authors, about, subscribe, contact, privacy",
     "lead story, latest articles, categories, newsletter sign-up, most read",
     "search, categories and tags, RSS, reading time, share links, author pages"),
    ("community", "Community portal", "personal", "Join now",
     "home, about, membership, events, members area (sign-in), news, contact, privacy",
     "hero with the community promise, benefits of joining, upcoming events, member stories (with consent), join form",
     "member sign-in, member directory (opt-in), events calendar, notices"),
    ("event", "Event microsite", "event", "Register",
     "home, agenda, speakers / artists, venue, tickets / register, FAQ, contact",
     "hero with date and place, countdown, highlights, agenda, speakers, venue map, register",
     "registration form, agenda by day, add-to-calendar, venue directions"),
    ("webapp", "Web app with dashboard", "admissions", "Start free / Sign up",
     "home, features, pricing, docs / help, sign in, sign up, dashboard, privacy, terms",
     "hero with a product shot, feature tour, use cases, pricing (her plans), security, FAQ",
     "sign-up and sign-in, a dashboard with her lists and charts, roles, data export"),
    ("marketplace", "Marketplace & directory", "catalogue", "Search / List yours",
     "home, browse (categories), listing page, list-yours, how it works, about, contact, privacy, terms",
     "search bar hero, categories, featured listings, how it works for both sides, trust and safety, join as seller",
     "search with filters, listing pages, seller sign-up she approves, enquiry or order flow"),
]


def subjects() -> list[tuple[str, str]]:
    """(sector key, subject) in a round-robin across sectors, so neighbours are always different fields."""
    out: list[tuple[str, str]] = []
    for i in range(20):
        for key, *_ in SECTORS:
            out.append((key, SUBJECTS[key][i]))
    return out


def check() -> list[str]:
    from . import library as L
    from . import taxonomy as T
    bad: list[str] = []
    F = L.fields()
    if len(SECTORS) != 50:
        bad.append(f"{len(SECTORS)} sectors, want 50")
    for key, label, field, *_ in SECTORS:
        if field not in F:
            bad.append(f"{key}: no library field {field}")
        if len(SUBJECTS.get(key, [])) != 20:
            bad.append(f"{key}: {len(SUBJECTS.get(key, []))} subjects, want 20")
    allsub = [s for _, s in subjects()]
    dup = {s for s in allsub if allsub.count(s) > 1}
    if len(TYPES) != 10:
        bad.append(f"{len(TYPES)} types, want 10")
    for t in TYPES:
        if t[2] not in T.GOALS:
            bad.append(f"type {t[0]}: no goal {t[2]}")
    if dup:
        bad.append(f"subject repeated: {sorted(dup)[:5]}")
    return bad


# ---------------------------------------------------------------- v0.686 one lakh UNIQUE websites
# Each template = one subject x one positioning x one world city = a business of its own, with its own coined name.
# 1,000 subjects x 10 positionings x 10 cities = 100,000 distinct websites; the website type and the design style are
# chosen per website (not multiplied), so no two cards are the same business.
ANGLES: list[str] = ["premium", "affordable", "eco-friendly", "family-owned", "modern", "heritage", "women-led", "boutique",
                     "community-first", "newly launched"]
# (city, country, currency sign)
CITIES: list[tuple[str, str, str]] = [
    ("Mumbai", "India", "₹"), ("Bengaluru", "India", "₹"), ("Dubai", "UAE", "AED "), ("London", "UK", "£"),
    ("New York", "USA", "$"), ("Singapore", "Singapore", "S$"), ("Sydney", "Australia", "A$"), ("Toronto", "Canada", "C$"),
    ("Nairobi", "Kenya", "KSh "), ("Berlin", "Germany", "€"),
]
# 330 short roots; every website gets a different pair of them as its working name (330 x 329 = 108,570 names).
ROOTS: list[str] = """
oak river blue north fern pine cedar maple birch willow amber coral pearl ivory jade onyx ruby opal sable slate
stone brook lake bay cove reef dune mesa ridge peak summit vale glen meadow field grove orchard garden bloom petal
lotus lily iris rose sage mint basil thyme clove saffron ginger pepper honey juniper cocoa coffee berry plum peach
lemon lime olive fig date mango kiwi cherry apricot quince sun moon star nova comet orbit lunar solar astra zenith
dawn dusk ember flame spark glow beam ray light lumen halo aura prism crystal quartz silver golden copper iron steel
bright clear true pure fresh swift brisk bold calm kind wise keen fair grand noble royal regal urban metro city town
harbor port anchor sail wave tide shore coast island atlas compass map trail path way bridge arch gate tower forge
mill loom craft hive nest den haven harbour home hearth lantern beacon signal pulse rhythm echo chord note tune
melody canvas brush ink quill page story fable tale saga epic myth spirit soul heart mind dream vision quest venture
voyage journey nomad rover ranger scout pilot captain falcon hawk eagle raven robin sparrow swallow heron crane swan
lark wren finch kestrel osprey tiger lion panther lynx fox wolf bear otter beaver badger hazel dolphin orca seal
koi panda koala zebra gazelle bison stag deer elk moose hare rabbit squirrel owl cardinal parrot peacock flamingo
indigo violet scarlet crimson azure cobalt teal cyan emerald aspen khaki ochre umber sienna charcoal ebony snow frost
rain cloud storm thunder breeze wind gale mist fog dew spring summer autumn winter season harvest seed sprout root
leaf branch bough timber cork bamboo jute cotton linen silk wool velvet satin denim tweed lace thread needle button
kettle spoon ladle oven cobble brew malt hops grain wheat barley rice millet corn bean lentil spice salt sugar
sorrel nectar syrup cream butter cheese bread crumb crust loaf pebble boulder canyon marble garnet topaz beryl flint nimbus sierra lagoon valley prairie tundra delta
""".split()
ROOTS = ROOTS[:330]


def check_roots() -> list[str]:
    bad = []
    seen = set()
    for r in ROOTS:
        if r in seen:
            bad.append(f"root repeated: {r}")
        seen.add(r)
    if len(ROOTS) < 330:
        bad.append(f"{len(ROOTS)} roots, want 330")
    return bad


# Which website types make sense for each sector (a booking site for an AI tool does not).
_TECH = "landing webapp company magazine community event"
_B2B = "company landing portfolio magazine event booking"
SECTOR_TYPES: dict[str, list[str]] = {k: v.split() for k, v in {
    "saas": _TECH, "ai": _TECH, "devtools": _TECH, "security": "company landing webapp magazine event booking",
    "enterprise": _B2B, "consulting": "company booking portfolio landing magazine event", "finance": "company booking landing magazine webapp event",
    "fintech": _TECH, "insurance": "company landing booking magazine webapp marketplace", "realestate": "company landing marketplace booking event magazine",
    "architecture": "portfolio company landing magazine booking event", "construction": _B2B, "manufacturing": "company landing store portfolio magazine marketplace",
    "energy": "company landing store booking magazine webapp", "auto": "company store booking marketplace landing event",
    "logistics": "company landing webapp booking marketplace magazine", "travel": "booking company landing magazine event marketplace",
    "hospitality": "booking company landing event magazine store", "food": "company store booking landing event magazine",
    "foodbrand": "store landing company magazine event community", "retail": "store company landing event marketplace magazine",
    "fashion": "store landing company magazine event portfolio", "beauty": "booking store company landing portfolio magazine",
    "health": "company booking landing magazine community event", "wellness": "booking company community landing store event",
    "pharma": "company landing store magazine event webapp", "school": "company landing event community magazine booking",
    "university": "company landing event community magazine webapp", "edtech": "landing webapp company community booking event",
    "research": "company magazine event community landing portfolio", "media": "magazine community landing company event store",
    "creative": "portfolio company landing magazine booking event", "photo": "portfolio booking store company landing magazine",
    "music": "event portfolio company store community landing", "gaming": "landing community event store company magazine",
    "events": "event booking company portfolio landing marketplace", "sports": "company booking community event store landing",
    "ngo": "company landing event community magazine store", "civic": "community company magazine event landing webapp",
    "faith": "company event community landing magazine booking", "legal": "company booking landing magazine portfolio event",
    "hr": "marketplace company landing webapp community event", "agri": "store company landing marketplace magazine event",
    "pets": "booking store company community landing event", "kids": "booking company event community store landing",
    "home": "booking company landing marketplace store magazine", "telecom": "company landing store webapp booking magazine",
    "crafts": "store portfolio community landing event magazine", "personal": "portfolio landing magazine booking store event",
    "community": "community event company magazine landing marketplace",
}.items()}
