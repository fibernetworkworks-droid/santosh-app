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
}
