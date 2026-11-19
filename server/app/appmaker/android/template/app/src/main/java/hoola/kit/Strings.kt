package hoola.kit

// Made by Hoola App Sahayak. The kit's own words in the app's language (hi = Hindi, mr = Marathi, hinglish, en).

object Strings {
    private var lang = "en"
    fun init(language: String) { lang = language }
    private fun t(en: String, hi: String, mr: String = hi, hing: String = en): String = when (lang) {
        "hi" -> hi; "mr" -> mr; "hinglish" -> hing; "en" -> en; else -> I18n.tr(en)    // v0.347 other languages: the build's table
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
    val myTeam get() = t("Team", "टीम", "टीम", "Team")
    val openWork get() = t("open", "बाकी", "बाकी", "baaki")
    val receipt get() = t("Receipt", "रसीद", "पावती", "Raseed")       // v0.354 RASEED
    val invoice get() = t("Tax invoice", "टैक्स इनवॉइस", "कर बीजक", "Tax invoice")   // v0.355 GST BILL
    val chat get() = t("Message the shop", "दुकान को संदेश", "दुकानाला संदेश", "Dukaan ko message")     // v0.378 BAAT
    val customerMessages get() = t("Customer messages", "ग्राहकों के संदेश", "ग्राहकांचे संदेश", "Graahakon ke message")
    val typeMessage get() = t("Type a message", "संदेश लिखें", "संदेश लिहा", "Message likhiye")
    val chatHint get() = t("Ask anything about your order or our products.", "अपने ऑर्डर या सामान के बारे में कुछ भी पूछें।", "तुमच्या ऑर्डर किंवा वस्तूंबद्दल काहीही विचारा.", "Apne order ya saamaan ke baare mein kuch bhi poochhiye.")
    val send get() = t("Send", "भेजें", "पाठवा", "Bhejiye")
    val shopOnline get() = t("Shop is online", "दुकान ऑनलाइन है", "दुकान ऑनलाइन आहे", "Dukaan online hai")       // v0.407 ABHI ABHI
    val isOnline get() = t("online", "ऑनलाइन", "ऑनलाइन", "online")
    val isTyping get() = t("typing…", "लिख रहे हैं…", "लिहित आहेत…", "likh rahe hain…")
    val live get() = t("Live", "लाइव", "लाइव्ह", "Live")
    // v0.425 RANG
    val signAgain get() = t("Sign again", "फिर से साइन करें", "फिर से साइन करें", "Phir se sign karein")
    val useSignature get() = t("Use this signature", "यह साइन लें", "यह साइन लें", "Yeh sign lein")
    val clearWord get() = t("Clear", "मिटाएँ", "मिटाएँ", "Mitayein")
    val addPhotos get() = t("Add photos", "फ़ोटो जोड़ें", "फ़ोटो जोड़ें", "Photos jodiye")
    val videoTooBig get() = t("The video did not open or is over 50 MB.", "वीडियो नहीं खुला या 50 MB से बड़ा है।", "वीडियो नहीं खुला या 50 MB से बड़ा है।", "Video nahi khula ya 50 MB se bada hai.")
    val videoReady get() = t("Video ready - it is sent with the form.", "वीडियो तैयार - फ़ॉर्म के साथ जाएगा।", "वीडियो तैयार - फ़ॉर्म के साथ जाएगा।", "Video taiyaar - form ke saath jayega.")
    val videoSaved get() = t("Video saved.", "वीडियो सेव है।", "वीडियो सेव है।", "Video save hai.")
    val addVideo get() = t("Add video", "वीडियो जोड़ें", "वीडियो जोड़ें", "Video jodiye")
    val changeVideo get() = t("Change video", "वीडियो बदलें", "वीडियो बदलें", "Video badlein")
    val recording get() = t("Recording…", "रिकॉर्ड हो रहा है…", "रिकॉर्ड हो रहा है…", "Record ho raha hai…")
    val record get() = t("Record", "रिकॉर्ड करें", "रिकॉर्ड करें", "Record karein")
    val recordAgain get() = t("Record again", "फिर रिकॉर्ड करें", "फिर रिकॉर्ड करें", "Phir record karein")
    val stopWord get() = t("Stop", "रोकें", "रोकें", "Rokein")
    val micDenied get() = t("Microphone not allowed. You can type instead.", "माइक की अनुमति नहीं मिली। लिख दीजिए।", "माइक की अनुमति नहीं मिली। लिख दीजिए।", "Mic ki anumati nahi mili. Likh dijiye.")
    val listWord get() = t("List", "सूची", "सूची", "List")
    val playVideo get() = t("Play video", "वीडियो चलाएँ", "वीडियो चलाएँ", "Video chalayein")
    val pauseWord get() = t("Pause", "रोकें", "रोकें", "Rokein")
    val playWord get() = t("Play", "चलाएँ", "चलाएँ", "Chalayein")
    val pdfFailed get() = t("The PDF did not open.", "PDF नहीं खुला।", "PDF नहीं खुला।", "PDF nahi khula.")
    val pageWord get() = t("Page", "पेज", "पेज", "Page")
    val prevWord get() = t("Back", "पीछे", "पीछे", "Peeche")
    val nextWord get() = t("Next", "आगे", "आगे", "Aage")
    val skipWord get() = t("Skip", "छोड़ें", "छोड़ें", "Chhodein")
    val doneWord get() = t("Done", "हो गया", "हो गया", "Ho gaya")
    val connDone get() = t("Done.", "हो गया।", "झाले.", "Ho gaya.")     // v0.424 JODO
    // v0.419 PAISA
    val payOnline get() = t("Pay online", "ऑनलाइन भुगतान", "ऑनलाइन पैसे भरा", "Online pay karein")
    val opening get() = t("Opening…", "खुल रहा है…", "उघडत आहे…", "Khul raha hai…")
    val payWaiting get() = t("Waiting for the payment to be confirmed by the gateway…", "गेटवे से भुगतान की पुष्टि का इंतज़ार…", "गेटवेकडून पेमेंटची खात्री होत आहे…", "Gateway se payment confirm hone ka intezaar…")
    val autoPay get() = t("AutoPay plans", "ऑटोपे प्लान", "ऑटोपे प्लॅन", "AutoPay plans")
    val autoPayOn get() = t("AutoPay on", "ऑटोपे चालू", "ऑटोपे चालू", "AutoPay chalu")
    val charged get() = t("payments made", "भुगतान हुए", "पेमेंट झाले", "payment hue")
    val cancelAutoPay get() = t("Cancel AutoPay", "ऑटोपे बंद करें", "ऑटोपे बंद करा", "AutoPay band karein")
    val autoPayOff get() = t("AutoPay cancelled. Nothing more will be charged.", "ऑटोपे बंद। आगे कुछ नहीं कटेगा।", "ऑटोपे बंद. पुढे काही कापले जाणार नाही.", "AutoPay band. Aage kuch nahi katega.")
    val autoPayWhy get() = t("Charged automatically {n} times through your bank's mandate. You approve it on the next page and can cancel any time here.", "आपके बैंक मैंडेट से {n} बार अपने आप कटेगा। अगले पेज पर आप मंज़ूर करेंगे, और यहाँ कभी भी बंद कर सकते हैं।", "तुमच्या बँक मँडेटमधून {n} वेळा आपोआप कापले जाईल. पुढील पानावर मंजूर करा, इथे कधीही बंद करू शकता.", "Aapke bank mandate se {n} baar apne aap katega. Agle page par aap manzoor karenge, aur yahan kabhi bhi band kar sakte hain.")
    val startAutoPay get() = t("Start AutoPay", "ऑटोपे शुरू करें", "ऑटोपे सुरू करा", "AutoPay shuru karein")
    // v0.412 NAKSHA LIVE
    val startShift get() = t("Start shift", "शिफ़्ट शुरू करें", "शिफ्ट सुरू करा", "Shift shuru karein")
    val endShift get() = t("End shift", "शिफ़्ट ख़त्म करें", "शिफ्ट संपवा", "Shift khatam karein")
    val onShift get() = t("On shift - sharing your location", "शिफ़्ट पर - आपकी लोकेशन शेयर हो रही है", "शिफ्टवर - तुमचे लोकेशन शेअर होत आहे", "Shift par - aapki location share ho rahi hai")
    val shiftNote get() = t("Customers see you only while you bring their order. Tap End shift in the app to stop.", "ग्राहक आपको सिर्फ़ तब देखते हैं जब आप उनका ऑर्डर ला रहे हों। रोकने के लिए ऐप में शिफ़्ट ख़त्म करें।", "ग्राहक तुम्हाला फक्त त्यांची ऑर्डर आणताना पाहतात. थांबवण्यासाठी ॲपमध्ये शिफ्ट संपवा.", "Graahak aapko sirf tab dekhte hain jab aap unka order la rahe hon. Rokne ke liye app mein End shift.")
    val shiftChannel get() = t("Shift location", "शिफ़्ट लोकेशन", "शिफ्ट लोकेशन", "Shift location")
    val shareTitle get() = t("Share your location during the shift?", "शिफ़्ट में अपनी लोकेशन शेयर करें?", "शिफ्टमध्ये लोकेशन शेअर करायचे?", "Shift mein apni location share karein?")
    val shareWhy get() = t("While your shift is on, this app sends your location to the shop - also when the app is in the background (you will see a notification the whole time). A customer sees you on a map only while you are bringing HER order. It stops the moment you tap End shift, and your location is then removed.", "जब तक शिफ़्ट चालू है, यह ऐप आपकी लोकेशन दुकान को भेजता है - ऐप पीछे होने पर भी (पूरे समय एक सूचना दिखेगी)। ग्राहक आपको नक्शे पर सिर्फ़ तब देखता है जब आप उसका ऑर्डर ला रहे हों। शिफ़्ट ख़त्म करते ही यह रुक जाता है और लोकेशन हटा दी जाती है।", "शिफ्ट चालू असेपर्यंत हे ॲप तुमचे लोकेशन दुकानाला पाठवते - ॲप मागे असतानाही (पूर्ण वेळ सूचना दिसेल). ग्राहक तुम्हाला नकाशावर फक्त त्याची ऑर्डर आणताना पाहतो. शिफ्ट संपवताच हे थांबते आणि लोकेशन काढले जाते.", "Jab tak shift chalu hai, yeh app aapki location dukaan ko bhejta hai - app peeche hone par bhi (poore samay ek notification dikhega). Graahak aapko map par sirf tab dekhta hai jab aap uska order la rahe hon. End shift karte hi yeh ruk jaata hai aur location hata di jaati hai.")
    val shiftOnNote get() = t("You are on shift. Your location is shared with the shop.", "आप शिफ़्ट पर हैं। आपकी लोकेशन दुकान के साथ शेयर हो रही है।", "तुम्ही शिफ्टवर आहात. तुमचे लोकेशन दुकानासोबत शेअर होत आहे.", "Aap shift par hain. Aapki location dukaan ke saath share ho rahi hai.")
    val shiftOffNote get() = t("Start your shift to share your location while you deliver.", "डिलीवरी के दौरान लोकेशन शेयर करने के लिए शिफ़्ट शुरू करें।", "डिलिव्हरी करताना लोकेशन शेअर करण्यासाठी शिफ्ट सुरू करा.", "Delivery ke dauraan location share karne ke liye shift shuru karein.")
    val updateForShift get() = t("Update the app to use shifts and live tracking.", "शिफ़्ट और लाइव ट्रैकिंग के लिए ऐप अपडेट करें।", "शिफ्ट आणि लाइव्ह ट्रॅकिंगसाठी ॲप अपडेट करा.", "Shift aur live tracking ke liye app update karein.")
    val trackLive get() = t("Track live", "लाइव देखें", "लाइव्ह पाहा", "Live dekhein")
    val hideMap get() = t("Hide map", "नक्शा छिपाएँ", "नकाशा लपवा", "Map chhupayein")
    val rider get() = t("Rider", "राइडर", "रायडर", "Rider")
    val yourPlace get() = t("Your place", "आपकी जगह", "तुमचे ठिकाण", "Aapki jagah")
    val onTheWay get() = t("on the way", "रास्ते में", "रस्त्यात", "raaste mein")
    val riderNear get() = t("The rider is near you", "राइडर आपके पास है", "रायडर तुमच्या जवळ आहे", "Rider aapke paas hai")
    val riderArrived get() = t("The rider has arrived", "राइडर पहुँच गया", "रायडर पोहोचला", "Rider pahunch gaya")
    val notOnTheWay get() = t("Live tracking starts when the order is on its way.", "ऑर्डर रास्ते में होने पर लाइव ट्रैकिंग शुरू होगी।", "ऑर्डर रस्त्यात असताना लाइव्ह ट्रॅकिंग सुरू होईल.", "Order raaste mein hone par live tracking shuru hogi.")
    val about get() = t("About", "लगभग", "सुमारे", "Lagbhag")
    val estimate get() = t("estimate", "अनुमान", "अंदाज", "andaaza")
    val ridersOnShift get() = t("Riders on shift", "शिफ़्ट पर राइडर", "शिफ्टवरील रायडर", "Shift par riders")
    val nobodyOnShift get() = t("Nobody is on shift right now.", "अभी कोई शिफ़्ट पर नहीं है।", "आता कोणीही शिफ्टवर नाही.", "Abhi koi shift par nahi hai.")
    val changeTime get() = t("Change time", "समय बदलें", "वेळ बदला", "Samay badlein")     // v0.377
    val cancelWord get() = t("Cancel", "रद्द", "रद्द", "Cancel")
    val pickSlot get() = t("Delivery time", "डिलीवरी का समय", "डिलिव्हरीची वेळ", "Delivery ka samay")   // v0.371 SLOT
    val noSlots get() = t("No slot free right now - the shop will call to fix a time.", "अभी कोई स्लॉट खाली नहीं - दुकान समय तय करने के लिए कॉल करेगी।", "आता कोणताही स्लॉट मोकळा नाही - दुकान वेळ ठरवण्यासाठी कॉल करेल.", "Abhi koi slot khaali nahi - dukaan call karke samay tay karegi.")
    val delivery get() = t("Delivery", "डिलीवरी", "डिलिव्हरी", "Delivery")    // v0.360 DELIVERY
    val freeAbove get() = t("free above", "इससे ऊपर मुफ़्त", "यापुढे मोफत", "is se upar free")
    val freeDelivery get() = t("Free delivery", "मुफ़्त डिलीवरी", "मोफत डिलिव्हरी", "Free delivery")
    val shopClosed get() = t("Shop is closed now - your order will be seen when it opens", "दुकान अभी बंद है - खुलते ही ऑर्डर देखा जाएगा", "दुकान आता बंद आहे - उघडताच ऑर्डर पाहिली जाईल", "Dukaan abhi band hai - khulte hi order dekha jayega")
    val areaOnly get() = t("Delivery only to some PIN codes - please put your PIN code in the address.", "डिलीवरी कुछ पिन कोड पर ही - पते में पिन कोड लिखें।", "डिलिव्हरी काही पिन कोडवरच - पत्त्यात पिन कोड लिहा.", "Delivery kuch PIN codes par hi - address mein PIN code likhein.")
    val myKhata get() = t("My ledger", "मेरा खाता", "माझे खाते", "Mera khata")     // v0.359 KHATA
    val due get() = t("To pay", "बाकी", "बाकी", "Baaki")
    val advance get() = t("Advance", "एडवांस", "आगाऊ", "Advance")
    val allClear get() = t("All clear", "सब चुकता", "सगळे चुकते", "Sab chukta")
    val khataDues get() = t("Credit due", "उधार", "उधार", "Udhaar")
    val received get() = t("Received", "मिला", "मिळाले", "Mila")
    val onCredit get() = t("On credit", "उधार पर", "उधारीवर", "Udhaar par")
    val giveCredit get() = t("On credit", "उधार दें", "उधार द्या", "Udhaar do")
    val couponCode get() = t("Coupon code", "कूपन कोड", "कूपन कोड", "Coupon code")    // v0.358 COUPON
    val apply get() = t("Apply", "लगाएँ", "लावा", "Lagayein")
    val couponSaved get() = t("You save", "आपकी बचत", "तुमची बचत", "Aapki bachat")
    val couponAgain get() = t("Cart changed: apply the code again.", "कार्ट बदला: कोड फिर से लगाएँ।", "कार्ट बदलला: कोड पुन्हा लावा.", "Cart badla: code phir lagayein.")
    val soldOut get() = t("Sold out", "स्टॉक खत्म", "स्टॉक संपला", "Stock khatam")    // v0.357 STOCK
    val creditNote get() = t("Credit note", "क्रेडिट नोट", "क्रेडिट नोट", "Credit note")   // v0.356 WAPSI
    // v0.353 RAAY
    val rateIt get() = t("How was it? Rate us", "कैसा रहा? रेटिंग दें", "कसे वाटले? रेटिंग द्या", "Kaisa raha? Rating dijiye")
    val ratingNote get() = t("A few words (optional)", "कुछ शब्द (ज़रूरी नहीं)", "थोडे शब्द (ऐच्छिक)", "Kuch shabd (zaroori nahi)")
    val sendRating get() = t("Send rating", "रेटिंग भेजें", "रेटिंग पाठवा", "Rating bhejiye")
    val thanksRating get() = t("Thank you!", "धन्यवाद!", "धन्यवाद!", "Shukriya!")
    // v0.352 KAAM BAANTO
    val myWork get() = t("My work", "मेरा काम", "माझे काम", "Mera kaam")
    val takeIt get() = t("I'll take it", "मैं करूँगा", "मी करतो", "Main karunga")
    val giveBack get() = t("Give back", "वापस दें", "परत द्या", "Wapas dein")
    val withPerson get() = t("With", "किसके पास", "कोणाकडे", "Kiske paas")
    val you get() = t("You", "आप", "तुम्ही", "Aap")
    val notAssigned get() = t("Not assigned", "किसी को नहीं दिया", "कोणालाही दिले नाही", "Kisi ko nahi diya")
    val onIt get() = t("is on it", "इस पर काम कर रहे हैं", "यावर काम करत आहेत", "is par kaam kar rahe hain")
    val assignedToYou get() = t("Given to you", "आपको सौंपा गया", "तुम्हाला दिले", "Aapko diya gaya")
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

    // v0.340 scan, dashboard, inbox
    val loading get() = t("Loading…", "लोड हो रहा है…", "लोड होत आहे…", "Load ho raha hai…")
    val total get() = t("Total", "कुल", "एकूण", "Total")
    val scan get() = t("Scan", "स्कैन करें", "स्कॅन करा", "Scan karein")
    val scanHint get() = t("Scan or type the code", "कोड स्कैन करें या लिखें", "कोड स्कॅन करा किंवा लिहा", "Code scan karein ya likhein")
    val scanFailed get() = t("Scanner not available. Type the code instead.", "स्कैनर नहीं चला। कोड लिख दें।", "स्कॅनर चालला नाही. कोड लिहा.", "Scanner nahi chala. Code likh dijiye.")
    val dashboard get() = t("Dashboard", "डैशबोर्ड", "डॅशबोर्ड", "Dashboard")
    val last14 get() = t("Last 14 days", "पिछले 14 दिन", "मागील 14 दिवस", "Pichhle 14 din")
    val inbox get() = t("Updates", "अपडेट", "अपडेट", "Updates")
    val inboxEmpty get() = t("No updates yet.", "अभी कोई अपडेट नहीं।", "अजून अपडेट नाहीत.", "Abhi koi update nahi.")
    // v0.346 documents
    val addFile get() = t("Attach PDF", "PDF जोड़ें", "PDF जोडा", "PDF jodiye")
    val changeFile get() = t("Change PDF", "PDF बदलें", "PDF बदला", "PDF badliye")
    val fileFailed get() = t("Please pick a PDF under 10 MB.", "10 MB से छोटी PDF चुनें।", "10 MB पेक्षा लहान PDF निवडा.", "10 MB se chhoti PDF chuniye.")
    // v0.382 DIMAAG: the app's logic (links, workflow, approvals)
    val approvals get() = t("Approvals", "मंज़ूरी", "मंजुरी", "Manzoori")
    val approve get() = t("Approve", "मंज़ूर करें", "मंजूर करा", "Manzoor")
    val reject get() = t("Reject", "मना करें", "नाकारा", "Mana")
    val waitingFor get() = t("Waiting for", "इंतज़ार", "प्रतीक्षा", "Intezaar")
    val needsApproval get() = t("needs approval", "मंज़ूरी चाहिए", "मंजुरी हवी", "manzoori chahiye")
    val noApprovals get() = t("Nothing waiting for you.", "आपके लिए कुछ नहीं रुका।", "तुमच्यासाठी काही थांबलेले नाही.", "Aapke liye kuch nahi ruka.")
    val note get() = t("Note", "टिप्पणी", "टीप", "Note")
    val choose get() = t("Choose", "चुनें", "निवडा", "Chuniye")
    val save get() = t("Save", "सहेजें", "जतन करा", "Save")
    val cancel get() = t("Cancel", "रद्द", "रद्द", "Cancel")
    val step get() = t("Step", "चरण", "पायरी", "Step")
    val askedBy get() = t("Asked by", "माँगा", "मागितले", "Maanga")
    val allLists get() = t("All lists", "सारी सूचियाँ", "सर्व याद्या", "Saari lists")
    // v0.435 PARIVAAR: the partner app's jobs screen
    val ptJobs get() = t("Jobs", "काम", "कामे", "Kaam")
    val ptLoginWhy get() = t("Sign in with your partner account to see your jobs.", "अपने काम देखने के लिए पार्टनर खाते से साइन इन करें।", "तुमची कामे पाहण्यासाठी पार्टनर खात्याने साइन इन करा.", "Apne kaam dekhne ke liye partner account se sign in karein.")
    val ptWaiting get() = t("Your application is waiting", "आपकी अर्ज़ी रुकी है", "तुमचा अर्ज प्रलंबित आहे", "Aapki arzi ruki hai")
    val ptWaitingWhy get() = t("The business will approve it. Jobs appear here after that.", "बिज़नेस इसे मंज़ूर करेगा। उसके बाद काम यहाँ दिखेंगे।", "व्यवसाय मंजूर करेल. त्यानंतर कामे इथे दिसतील.", "Business ise manzoor karega. Uske baad kaam yahan dikhenge.")
    val ptApply get() = t("Become a partner", "पार्टनर बनें", "पार्टनर व्हा", "Partner baniye")
    val ptApplyWhy get() = t("Send an application. The business approves every partner itself.", "अर्ज़ी भेजें। हर पार्टनर को बिज़नेस खुद मंज़ूर करता है।", "अर्ज पाठवा. प्रत्येक पार्टनरला व्यवसाय स्वतः मंजूर करतो.", "Arzi bhejiye. Har partner ko business khud manzoor karta hai.")
    val ptApplyBtn get() = t("Send application", "अर्ज़ी भेजें", "अर्ज पाठवा", "Arzi bhejiye")
    val ptMine get() = t("My jobs", "मेरे काम", "माझी कामे", "Mere kaam")
    val ptNew get() = t("New jobs", "नए काम", "नवीन कामे", "Naye kaam")
    val ptPast get() = t("Finished", "पूरे हुए", "पूर्ण झाली", "Poore hue")
    val ptNone get() = t("Nothing for you right now.", "अभी आपके लिए कुछ नहीं।", "आत्ता तुमच्यासाठी काही नाही.", "Abhi aapke liye kuch nahi.")
    val ptNoOffers get() = t("No new jobs right now.", "अभी कोई नया काम नहीं।", "आत्ता नवीन काम नाही.", "Abhi koi naya kaam nahi.")
    val ptTake get() = t("Take this job", "यह काम लें", "हे काम घ्या", "Yeh kaam lein")
    val ptRoute get() = t("Route", "रास्ता", "रस्ता", "Raasta")
    val ptRefresh get() = t("Refresh", "ताज़ा करें", "रिफ्रेश करा", "Taaza karein")
    val ptRetry get() = t("Try again", "फिर कोशिश करें", "पुन्हा प्रयत्न करा", "Phir koshish karein")
    // v0.455 SURAKSHIT LOGIN
    val sgPhone get() = t("Mobile number", "मोबाइल नंबर", "मोबाइल नंबर", "Mobile number")
    val sgSendCode get() = t("Send the code", "कोड भेजें", "कोड पाठवा", "Code bhejiye")
    val sgSentTo get() = t("Code sent to", "कोड भेजा गया", "कोड पाठवला", "Code bheja gaya")
    val sgCode get() = t("6-digit code", "6 अंकों का कोड", "6 अंकी कोड", "6 ank ka code")
    val sgAgain get() = t("Change number / send again", "नंबर बदलें / फिर भेजें", "नंबर बदला / पुन्हा पाठवा", "Number badlein / phir bhejiye")
    val sgUseEmail get() = t("Use email instead", "ईमेल से करें", "ईमेलने करा", "Email se karein")
    val sgUsePhone get() = t("Use mobile number instead", "मोबाइल नंबर से करें", "मोबाइल नंबरने करा", "Mobile number se karein")
    val sgConsent get() = t("I agree to the privacy notice", "मैं प्राइवेसी नोटिस से सहमत हूँ", "मी प्रायव्हसी नोटिसला सहमत आहे", "Main privacy notice se sehmat hoon")
    val sgNever get() = t("The code goes only into this box. Nobody from this business or Hoola will ever ask you for it.",
        "कोड सिर्फ इसी बॉक्स में डालें। यह बिज़नेस या Hoola आपसे कोड कभी नहीं माँगेगा।",
        "कोड फक्त याच बॉक्समध्ये टाका. हा व्यवसाय किंवा Hoola तुमचा कोड कधीच मागणार नाही.",
        "Code sirf isi box mein daaliye. Yeh business ya Hoola aapse code kabhi nahi maangega.")
    val sgGoogle get() = t("Continue with Google", "Google से जारी रखें", "Google ने पुढे जा", "Google se aage badhiye")
    val sgSecurity get() = t("Security", "सुरक्षा", "सुरक्षा", "Suraksha")
    val sgLogins get() = t("Where you are signed in", "आप कहाँ साइन इन हैं", "तुम्ही कुठे साइन इन आहात", "Aap kahan sign in hain")
    val sgThisPhone get() = t("this phone", "यही फ़ोन", "हाच फोन", "yahi phone")
    val sgEnd get() = t("Sign out", "साइन आउट", "साइन आउट", "Sign out")
    val sgEndAll get() = t("Sign out everywhere", "हर जगह से साइन आउट", "सर्वत्र साइन आउट", "Har jagah se sign out")
    val sg2fa get() = t("Second step (authenticator)", "दूसरा चरण (ऑथेंटिकेटर)", "दुसरी पायरी (ऑथेंटिकेटर)", "Doosra step (authenticator)")
    val sg2faWhy get() = t("Staff accounts can add a 6-digit code from an authenticator app as a second step.",
        "स्टाफ अकाउंट दूसरे चरण के लिए ऑथेंटिकेटर ऐप का 6 अंकों का कोड जोड़ सकते हैं।",
        "स्टाफ अकाउंट दुसऱ्या पायरीसाठी ऑथेंटिकेटर ॲपचा 6 अंकी कोड जोडू शकतात.",
        "Staff account doosre step ke liye authenticator app ka 6 ank ka code jod sakte hain.")
    val sg2faStart get() = t("Turn it on", "चालू करें", "चालू करा", "Chalu karein")
    val sg2faAdd get() = t("Add this key in your authenticator app, then type the code it shows.",
        "यह की अपने ऑथेंटिकेटर ऐप में डालें, फिर उसका कोड लिखें।", "ही की तुमच्या ऑथेंटिकेटर ॲपमध्ये टाका, नंतर कोड लिहा.",
        "Yeh key apne authenticator app mein daaliye, phir uska code likhiye.")
    val sg2faOn get() = t("Second step is on.", "दूसरा चरण चालू है।", "दुसरी पायरी चालू आहे.", "Doosra step chalu hai.")
    val sg2faIsOn get() = t("Second step is on for this account.", "इस अकाउंट पर दूसरा चरण चालू है।", "या अकाउंटवर दुसरी पायरी चालू आहे.", "Is account par doosra step chalu hai.")
    val sg2faOff get() = t("Turn it off", "बंद करें", "बंद करा", "Band karein")
    val sg2faMust get() = t("The business asks every staff account to keep the second step on.",
        "बिज़नेस चाहता है कि हर स्टाफ अकाउंट पर दूसरा चरण चालू रहे।", "व्यवसायाची अपेक्षा आहे की प्रत्येक स्टाफ अकाउंटवर दुसरी पायरी चालू राहावी.",
        "Business chahta hai ki har staff account par doosra step chalu rahe.")
    val sgMyData get() = t("My data", "मेरी जानकारी", "माझी माहिती", "Meri jaankari")
    val sgMyDataWhy get() = t("Take a copy of everything this account has here.", "इस अकाउंट की सारी जानकारी की कॉपी लें।",
        "या अकाउंटची सर्व माहितीची कॉपी घ्या.", "Is account ki saari jaankari ki copy lijiye.")
    val sgMyDataGet get() = t("Copy my data", "मेरी जानकारी कॉपी करें", "माझी माहिती कॉपी करा", "Meri jaankari copy karein")
    val sgMyDataReady get() = t("Copied. Paste it anywhere to keep it.", "कॉपी हो गई। कहीं पेस्ट कर लें।", "कॉपी झाली. कुठेही पेस्ट करा.", "Copy ho gayi. Kahin paste kar lijiye.")

    // v0.802 DEVICE: lock, rate, calendar, contacts, photo labels
    val unlockTitle get() = t("Private screen", "निजी स्क्रीन", "खाजगी स्क्रीन", "Private screen")
    val unlock get() = t("Unlock", "खोलें", "उघडा", "Kholiye")
    val lockFailed get() = t("Could not confirm it's you. Try again.", "पुष्टि नहीं हो पाई। फिर कोशिश करें।",
        "खात्री झाली नाही. पुन्हा प्रयत्न करा.", "Confirm nahi ho paya. Phir koshish karein.")
    val lockOld get() = t("This phone cannot use fingerprint here.", "इस फ़ोन पर यहाँ फ़िंगरप्रिंट नहीं चलता।",
        "या फोनवर इथे फिंगरप्रिंट चालत नाही.", "Is phone par yahan fingerprint nahi chalta.")
    val noLock get() = t("This phone has no screen lock, so it opens directly.", "इस फ़ोन पर स्क्रीन लॉक नहीं है, इसलिए सीधे खुल गया।",
        "या फोनला स्क्रीन लॉक नाही, म्हणून थेट उघडले.", "Is phone par screen lock nahi hai, isliye seedha khul gaya.")
    val rateApp get() = t("Rate this app", "ऐप को रेटिंग दें", "ॲपला रेटिंग द्या", "App ko rating dein")
    val addCalendar get() = t("Add to calendar", "कैलेंडर में जोड़ें", "कॅलेंडरमध्ये जोडा", "Calendar mein jodiye")
    val noCalendar get() = t("No calendar app on this phone.", "इस फ़ोन पर कैलेंडर ऐप नहीं है।", "या फोनवर कॅलेंडर ॲप नाही.", "Is phone par calendar app nahi hai.")
    val pickContact get() = t("Pick from contacts", "कॉन्टैक्ट से चुनें", "संपर्कातून निवडा", "Contacts se chuniye")
    val noContact get() = t("No phone number for that contact.", "उस कॉन्टैक्ट का फ़ोन नंबर नहीं मिला।", "त्या संपर्काचा फोन नंबर मिळाला नाही.", "Us contact ka phone number nahi mila.")
    val photo get() = t("Photo", "फ़ोटो", "फोटो", "Photo")
}
