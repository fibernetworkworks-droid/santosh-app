package hoola.kit

// Made by Hoola App Sahayak. The kit's own words in the app's language (hi = Hindi, mr = Marathi, hinglish, en).

object Strings {
    private var lang = "en"
    fun init(language: String) { lang = language }
    private fun t(en: String, hi: String, mr: String = hi, hing: String = en): String = when (lang) {
        "hi" -> hi; "mr" -> mr; "hinglish" -> hing; else -> en
    }

    val back get() = t("Back", "वापस", "मागे", "Wapas")
    val menu get() = t("Menu", "मेनू", "मेनू", "Menu")
    val add get() = t("ADD", "जोड़ें", "जोडा", "ADD")
    val less get() = t("Less", "कम", "कमी", "Kam")
    val more get() = t("More", "ज़्यादा", "जास्त", "Zyada")
    val search get() = t("Search", "खोजें", "शोधा", "Khojiye")
    val demo get() = t("Sample data for now: your real data appears when your Hoola sends it.",
        "अभी नमूना जानकारी है: आपकी असली जानकारी Hoola से आएगी।", "सध्या नमुना माहिती आहे: तुमची खरी माहिती Hoola कडून येईल.",
        "Abhi namuna data hai: asli data aapke Hoola se aayega.")
    val call get() = t("Call", "कॉल करें", "कॉल करा", "Call karein")
    val whatsapp get() = t("WhatsApp", "WhatsApp", "WhatsApp", "WhatsApp")
    val share get() = t("Share", "शेयर करें", "शेअर करा", "Share")
    val payUpi get() = t("Pay by UPI", "UPI से भुगतान", "UPI ने पैसे द्या", "UPI se pay karein")
    val upiCopied get() = t("UPI ID copied. Paste it in your UPI app.", "UPI ID कॉपी हो गई। अपने UPI ऐप में डालें।",
        "UPI ID कॉपी झाली. तुमच्या UPI ॲपमध्ये टाका.", "UPI ID copy ho gayi. Apne UPI app mein paste karein.")
    val noUpi get() = t("Payment details are not set yet.", "भुगतान की जानकारी अभी नहीं है।", "पेमेंटची माहिती अजून नाही.", "Payment ki jaankari abhi nahi hai.")
    val noPhone get() = t("Phone number not set yet.", "फ़ोन नंबर अभी नहीं है।", "फोन नंबर अजून नाही.", "Phone number abhi nahi hai.")
    val done get() = t("Done", "हो गया", "झाले", "Ho gaya")
    val cont get() = t("Continue", "आगे बढ़ें", "पुढे जा", "Aage badhiye")
    val later get() = t("Not now", "अभी नहीं", "आत्ता नाही", "Abhi nahi")
    val allow get() = t("Allow", "अनुमति दें", "परवानगी द्या", "Haan, allow")
    val agree get() = t("I agree to the use of my data as described", "मैं ऊपर लिखे अनुसार अपनी जानकारी के उपयोग से सहमत हूँ",
        "वर लिहिल्याप्रमाणे माझ्या माहितीच्या वापरास माझी संमती आहे", "Main upar likhe tareeke se apni jaankari ke use se sehmat hoon")
    val consentTitle get() = t("Your data", "आपकी जानकारी", "तुमची माहिती", "Aapki jaankari")
    val consentWhat get() = t("We keep your name, phone number and your orders / bookings to serve you. We don't sell it. You can withdraw consent or delete your account any time from Profile.",
        "आपकी सेवा के लिए हम आपका नाम, फ़ोन नंबर और ऑर्डर / बुकिंग रखते हैं। हम इसे बेचते नहीं। आप कभी भी प्रोफ़ाइल से सहमति वापस ले सकते हैं या अकाउंट हटा सकते हैं।",
        "तुमच्या सेवेसाठी आम्ही तुमचे नाव, फोन नंबर आणि ऑर्डर / बुकिंग ठेवतो. आम्ही ते विकत नाही. प्रोफाइलमधून कधीही संमती मागे घेऊ शकता किंवा अकाउंट हटवू शकता.",
        "Aapki seva ke liye hum aapka naam, phone number aur orders / bookings rakhte hain. Hum ise bechte nahi. Profile se kabhi bhi sehmati wapas ya account delete kar sakte hain.")
    val notifyTitle get() = t("Stay updated", "अपडेट पाते रहें", "अपडेट मिळवत रहा", "Updates paate rahiye")
    val notifyWhy get() = t("We'll notify you only about your orders, bookings and replies. You can turn it off any time.",
        "हम सिर्फ़ आपके ऑर्डर, बुकिंग और जवाबों की सूचना देंगे। आप कभी भी बंद कर सकते हैं।",
        "आम्ही फक्त तुमच्या ऑर्डर, बुकिंग आणि उत्तरांबद्दल सूचना देऊ. कधीही बंद करू शकता.",
        "Sirf aapke orders, bookings aur jawabon ki suchna denge. Kabhi bhi band kar sakte hain.")
    val seller get() = t("Seller details", "विक्रेता की जानकारी", "विक्रेत्याची माहिती", "Seller ki jaankari")
    val grievance get() = t("Grievance officer", "शिकायत अधिकारी", "तक्रार अधिकारी", "Shikayat adhikari")
    val grievanceNote get() = t("Complaints are acknowledged within 48 hours and resolved within one month.",
        "शिकायत की पावती 48 घंटे में और समाधान एक महीने में।", "तक्रारीची पोच 48 तासांत आणि निवारण एका महिन्यात.",
        "Shikayat ki pawti 48 ghante mein, hal ek mahine mein.")
    val privacy get() = t("Privacy policy", "प्राइवेसी नीति", "गोपनीयता धोरण", "Privacy policy")
    val deleteTitle get() = t("Delete account", "अकाउंट हटाएँ", "अकाउंट हटवा", "Account delete karein")
    val deleteWhat get() = t("Your account and personal data will be erased within 30 days. Bills we must keep by law are kept, without your contact details.",
        "आपका अकाउंट और निजी जानकारी 30 दिन में मिटा दी जाएगी। कानूनन रखने वाले बिल आपकी संपर्क जानकारी के बिना रखे जाएँगे।",
        "तुमचे अकाउंट आणि वैयक्तिक माहिती 30 दिवसांत पुसली जाईल. कायद्याने ठेवायची बिले तुमच्या संपर्क माहितीशिवाय ठेवली जातील.",
        "Aapka account aur niji jaankari 30 din mein mita di jayegi. Kanoonan rakhne wale bill bina contact details ke rakhe jayenge.")
    val deleteYes get() = t("Yes, delete my account", "हाँ, मेरा अकाउंट हटाएँ", "हो, माझे अकाउंट हटवा", "Haan, mera account hatao")
    val deleteDone get() = t("Request received. Your account will be deleted.", "अनुरोध मिल गया। आपका अकाउंट हटा दिया जाएगा।",
        "विनंती मिळाली. तुमचे अकाउंट हटवले जाईल.", "Request mil gayi. Aapka account hata diya jayega.")
    val name get() = t("Name", "नाम", "नाव", "Naam")
    val phone get() = t("Phone", "फ़ोन", "फोन", "Phone")
    val email get() = t("Email", "ईमेल", "ईमेल", "Email")
    val address get() = t("Address", "पता", "पत्ता", "Pata")
    val hours get() = t("Hours", "समय", "वेळ", "Samay")

    // v0.314 accounts + saved data
    val loginTitle get() = t("Sign in", "साइन इन", "साइन इन", "Sign in")
    val signupTitle get() = t("Create account", "अकाउंट बनाएँ", "अकाउंट तयार करा", "Account banaiye")
    val login get() = t("Sign in", "साइन इन करें", "साइन इन करा", "Sign in karein")
    val signup get() = t("Create account", "अकाउंट बनाएँ", "अकाउंट तयार करा", "Account banaiye")
    val loginWhy get() = t("Sign in to place orders, book and see what you asked for.", "ऑर्डर, बुकिंग और अपनी जानकारी देखने के लिए साइन इन करें।",
        "ऑर्डर, बुकिंग आणि तुमची माहिती पाहण्यासाठी साइन इन करा.", "Order, booking aur apni jaankari dekhne ke liye sign in karein.")
    val signupWhy get() = t("Your email and a password of 8 or more letters. Nothing else is needed.", "आपका ईमेल और कम से कम 8 अक्षरों का पासवर्ड। और कुछ नहीं चाहिए।",
        "तुमचा ईमेल आणि किमान 8 अक्षरांचा पासवर्ड. बाकी काही नको.", "Aapka email aur kam se kam 8 akshar ka password. Aur kuch nahi chahiye.")
    val password get() = t("Password", "पासवर्ड", "पासवर्ड", "Password")
    val haveAccount get() = t("I already have an account", "मेरा अकाउंट पहले से है", "माझे अकाउंट आधीच आहे", "Mera account pehle se hai")
    val newHere get() = t("New here? Create an account", "नए हैं? अकाउंट बनाएँ", "नवीन आहात? अकाउंट तयार करा", "Naye hain? Account banaiye")
    val account get() = t("My account", "मेरा अकाउंट", "माझे अकाउंट", "Mera account")
    val notSignedIn get() = t("You are not signed in", "आप साइन इन नहीं हैं", "तुम्ही साइन इन केलेले नाही", "Aap sign in nahi hain")
    val logout get() = t("Sign out", "साइन आउट", "साइन आउट", "Sign out")
    val staff get() = t("Staff", "स्टाफ़", "स्टाफ", "Staff")
    val nothingYet get() = t("Nothing here yet.", "अभी यहाँ कुछ नहीं है।", "अजून इथे काही नाही.", "Abhi yahan kuch nahi hai.")
    val sending get() = t("Sending…", "भेज रहे हैं…", "पाठवत आहे…", "Bhej rahe hain…")
    val saved get() = t("Saved. It reaches us as soon as you are online.", "सेव हो गया। ऑनलाइन होते ही हम तक पहुँच जाएगा।",
        "सेव झाले. ऑनलाइन होताच आमच्यापर्यंत पोहोचेल.", "Save ho gaya. Online hote hi hum tak pahunch jayega.")
    val pending get() = t("waiting to send", "भेजना बाकी", "पाठवणे बाकी", "bhejna baaki")
    val offline get() = t("No internet. Please try again.", "इंटरनेट नहीं है। फिर कोशिश करें।", "इंटरनेट नाही. पुन्हा प्रयत्न करा.", "Internet nahi hai. Phir koshish karein.")
    val tryAgain get() = t("Something went wrong. Please try again.", "कुछ गड़बड़ हुई। फिर कोशिश करें।", "काहीतरी चुकले. पुन्हा प्रयत्न करा.", "Kuch gadbad hui. Phir koshish karein.")
    val loginAgain get() = t("Please sign in again.", "कृपया फिर से साइन इन करें।", "कृपया पुन्हा साइन इन करा.", "Kripya phir se sign in karein.")
    val loginFirst get() = t("Sign in first, then it is saved.", "पहले साइन इन करें, फिर सेव होगा।", "आधी साइन इन करा, मग सेव होईल.", "Pehle sign in karein, phir save hoga.")
    val notSaved get() = t("It could not be saved.", "सेव नहीं हो पाया।", "सेव झाले नाही.", "Save nahi ho paya.")
    val staffOnly get() = t("Only staff can add this.", "इसे सिर्फ़ स्टाफ़ जोड़ सकता है।", "हे फक्त स्टाफ जोडू शकतो.", "Ise sirf staff jod sakta hai.")
    val required get() = t("please fill this", "यह भरना ज़रूरी है", "हे भरणे आवश्यक आहे", "yeh bharna zaroori hai")
    val cartEmpty get() = t("Your cart is empty.", "आपका कार्ट खाली है।", "तुमची कार्ट रिकामी आहे.", "Aapka cart khaali hai.")
    val staffView get() = t("Everyone's entries (staff view)", "सबकी एंट्री (स्टाफ़)", "सर्वांच्या नोंदी (स्टाफ)", "Sabki entries (staff)")
    val deleting get() = t("Deleting…", "हटा रहे हैं…", "हटवत आहे…", "Hata rahe hain…")

    // v0.319 photos, location, notifications, UPI paid, search
    val addPhoto get() = t("Add photo", "फ़ोटो जोड़ें", "फोटो जोडा", "Photo jodiye")
    val changePhoto get() = t("Change photo", "फ़ोटो बदलें", "फोटो बदला", "Photo badliye")
    val remove get() = t("Remove", "हटाएँ", "काढा", "Hataiye")
    val photoFailed get() = t("That photo could not be used.", "यह फ़ोटो नहीं लग पाई।", "हा फोटो वापरता आला नाही.", "Yeh photo nahi lag payi.")
    val useMyLocation get() = t("Use my location", "मेरी लोकेशन लें", "माझे लोकेशन घ्या", "Meri location lijiye")
    val finding get() = t("Finding…", "ढूँढ रहे हैं…", "शोधत आहे…", "Dhoondh rahe hain…")
    val openMap get() = t("Map", "नक्शा", "नकाशा", "Map")
    val locationTitle get() = t("Use your location?", "आपकी लोकेशन लें?", "तुमचे लोकेशन घ्यायचे?", "Aapki location lein?")
    val locationWhy get() = t("Only to fill this address, only now while the app is open. It is saved with this entry and nowhere else.",
        "सिर्फ़ यह पता भरने के लिए, सिर्फ़ अभी जब ऐप खुला है। यह इसी एंट्री के साथ सेव होगी, और कहीं नहीं।",
        "फक्त हा पत्ता भरण्यासाठी, फक्त आत्ता ॲप उघडे असताना. हे फक्त या नोंदीसोबत सेव होईल.",
        "Sirf yeh pata bharne ke liye, sirf abhi jab app khula hai. Yeh isi entry ke saath save hogi, aur kahin nahi.")
    val locationDenied get() = t("Location not allowed. You can type the address.", "लोकेशन की अनुमति नहीं मिली। पता लिख दीजिए।",
        "लोकेशनची परवानगी नाही. पत्ता लिहा.", "Location ki ijaazat nahi mili. Pata likh dijiye.")
    val locationFailed get() = t("Could not find the location. Please type the address.", "लोकेशन नहीं मिली। पता लिख दीजिए।",
        "लोकेशन सापडले नाही. पत्ता लिहा.", "Location nahi mili. Pata likh dijiye.")
    val iPaid get() = t("I have paid", "मैंने भुगतान कर दिया", "मी पैसे दिले", "Maine pay kar diya")
    val utr get() = t("UPI reference / UTR", "UPI रेफ़रेंस / UTR", "UPI संदर्भ / UTR", "UPI reference / UTR")
    val utrWhy get() = t("Type the 12-digit reference from your UPI app. The shop checks it in its own bank.",
        "अपने UPI ऐप से 12 अंकों का रेफ़रेंस लिखें। दुकान अपने बैंक में जाँच लेगी।",
        "तुमच्या UPI ॲपमधील 12 अंकी संदर्भ लिहा. दुकान आपल्या बँकेत तपासेल.",
        "Apne UPI app se 12 ank ka reference likhiye. Dukaan apne bank mein check kar legi.")
    val paidSaid get() = t("Thanks! The shop will confirm your payment.", "धन्यवाद! दुकान आपका भुगतान पक्का करेगी।",
        "धन्यवाद! दुकान तुमचे पेमेंट पक्के करेल.", "Shukriya! Dukaan aapka payment pakka karegi.")
    val updatesChannel get() = t("Order updates", "ऑर्डर अपडेट", "ऑर्डर अपडेट", "Order updates")
    val newEntry get() = t("New — open the app to see it", "नया — देखने के लिए ऐप खोलें", "नवीन — पाहण्यासाठी ॲप उघडा", "Naya — dekhne ke liye app kholiye")
    val all get() = t("All", "सभी", "सर्व", "Sab")

    // v0.325 updates
    val updateTitle get() = t("New version", "नया वर्ज़न", "नवीन आवृत्ती", "Naya version")
    val update get() = t("Update", "अपडेट करें", "अपडेट करा", "Update karein")
}
