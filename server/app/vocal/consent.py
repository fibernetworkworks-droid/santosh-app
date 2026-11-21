"""v0.999.89 HOOLA VOCAL GLOBAL - the consent statement a person reads aloud before Google's engine may copy their voice.

Copied character for character from the "Supported consent phrases by language" table on
aistudio.google.com/docs/voice-replication (read 21 Nov 2026; some lines have no final full stop on the page and are kept
so). Google's rule: the consent recording "must clearly recite the exact statement" in one of these locales, by the same
adult as the voice sample. A language without a statement here gets the English one, and the page says so.
"""
from __future__ import annotations

STATEMENTS: dict[str, str] = {
    'ar-XA': 'أنا مالك هذا الصوت وأوافق على أن تستخدم Google هذا الصوت لإنشاء نموذج صوتي اصطناعي.',
    'bn-IN': 'আমি এই ভয়েসের মালিক এবং আমি একটি সিন্থেটিক ভয়েস মডেল তৈরি করতে এই ভয়েস ব্যবহার করে Google-এর সাথে সম্মতি দিচ্ছি।',
    'zh-CN': '我是此声音的拥有者并授权谷歌使用此声音创建语音合成模型',
    'nl-NL': 'Ik ben de eigenaar van deze stem en ik geef Google toestemming om deze stem te gebruiken om een synthetisch stemmodel te maken.',
    'en-US': 'I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model.',
    'en-GB': 'I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model.',
    'en-IN': 'I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model.',
    'en-AU': 'I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model.',
    'fr-FR': "Je suis le propriétaire de cette voix et j'autorise Google à utiliser cette voix pour créer un modèle de voix synthétique.",
    'fr-CA': "Je suis le propriétaire de cette voix et j'autorise Google à utiliser cette voix pour créer un modèle de voix synthétique.",
    'de-DE': 'Ich bin der Eigentümer dieser Stimme und bin damit einverstanden, dass Google diese Stimme zur Erstellung eines synthetischen Stimmmodells verwendet.',
    'gu-IN': 'હું આ વોઈસનો માલિક છું અને સિન્થેટિક વોઈસ મોડલ બનાવવા માટે આ વોઈસનો ઉપયોગ કરીને google ને હું સંમતિ આપું છું',
    'hi-IN': 'मैं इस आवाज का मालिक हूं और मैं सिंथेटिक आवाज मॉडल बनाने के लिए Google को इस आवाज का उपयोग करने की सहमति देता हूं',
    'id-ID': 'Saya pemilik suara ini dan saya menyetujui Google menggunakan suara ini untuk membuat model suara sintetis.',
    'it-IT': 'Sono il proprietario di questa voce e acconsento che Google la utilizzi per creare un modello di voce sintetica.',
    'ja-JP': '私はこの音声の所有者であり、Googleがこの音声を使用して音声合成モデルを作成することを承認します。',
    'kn-IN': 'ನಾನು ಈ ಧ್ವನಿಯ ಮಾಲಿಕ ಮತ್ತು ಸಂಶ್ಲೇಷಿತ ಧ್ವನಿ ಮಾದರಿಯನ್ನು ರಚಿಸಲು ಈ ಧ್ವನಿಯನ್ನು ಬಳಸಿಕೊಂಡುಗೂಗಲ್ ಗೆ ನಾನು ಸಮ್ಮತಿಸುತ್ತೇನೆ.',
    'ko-KR': '나는 이 음성의 소유자이며 구글이 이 음성을 사용하여 음성 합성 모델을 생성할 것을 허용합니다.',
    'ml-IN': 'ഈ ശബ്ദത്തിന്റെ ഉടമ ഞാനാണ്, ഒരു സിന്തറ്റിക് വോയ്സ് മോഡൽ സൃഷ്ടിക്കാൻ ഈ ശബ്ദം ഉപയോഗിക്കുന്നതിന് ഞാൻ Google-ന് സമ്മതം നൽകുന്നു.',
    'mr-IN': 'मी या आवाजाचा मालक आहे आणि सिंथेटिक व्हॉइस मॉडेल तयार करण्यासाठी हा आवाज वापरण्यासाठी मी Google ला संमती देतो',
    'pl-PL': 'Jestem właścicielem tego głosu i wyrażam zgodę na wykorzystanie go przez Google w celu utworzenia syntetycznego modelu głosu.',
    'pt-BR': 'Eu sou o proprietário desta voz e autorizo o Google a usá-la para criar um modelo de voz sintética.',
    'ru-RU': 'Я являюсь владельцем этого голоса и даю согласие Google на использование этого голоса для создания модели синтетического голоса.',
    'es-ES': 'Soy el propietario de esta voz y doy mi consentimiento para que Google la utilice para crear un modelo de voz sintética.',
    'es-US': 'Soy el propietario de esta voz y doy mi consentimiento para que Google la utilice para crear un modelo de voz sintética.',
    'ta-IN': 'நான் இந்த குரலின் உரிமையாளர் மற்றும் செயற்கை குரல் மாதிரியை உருவாக்க இந்த குரலை பயன்படுத்த குகல்க்கு நான் ஒப்புக்கொள்கிறேன்.',
    'te-IN': 'నేను ఈ వాయిస్ యజమానిని మరియు సింతటిక్ వాయిస్ మోడల్ ని రూపొందించడానికి ఈ వాయిస్ ని ఉపయోగించడానికి googleకి నేను సమ్మతిస్తున్నాను.',
    'th-TH': 'ฉันเป็นเจ้าของเสียงนี้ และฉันยินยอมให้ Google ใช้เสียงนี้เพื่อสร้างแบบจำลองเสียงสังเคราะห์',
    'tr-TR': "Bu sesin sahibi benim ve Google'ın bu sesi kullanarak sentetik bir ses modeli oluşturmasına izin veriyorum.",
    'vi-VN': 'Tôi là chủ sở hữu giọng nói này và tôi đồng ý cho Google sử dụng giọng nói này để tạo mô hình giọng nói tổng hợp.',
}
_LOCALE = {"ar": "ar-XA", "bn": "bn-IN", "zh": "zh-CN", "nl": "nl-NL", "en": "en-US", "fr": "fr-FR", "de": "de-DE",
           "gu": "gu-IN", "hi": "hi-IN", "id": "id-ID", "it": "it-IT", "ja": "ja-JP", "kn": "kn-IN", "ko": "ko-KR",
           "ml": "ml-IN", "mr": "mr-IN", "pl": "pl-PL", "pt": "pt-BR", "ru": "ru-RU", "es": "es-ES", "ta": "ta-IN",
           "te": "te-IN", "th": "th-TH", "tr": "tr-TR", "vi": "vi-VN"}
ENGLISH = STATEMENTS["en-US"]


def line_for(code: str) -> dict:
    """The statement to read for a language code: {line, english, locale, own: bool}. own=False = English fallback."""
    loc = _LOCALE.get((code or "").split("-")[0].lower())
    if loc:
        return {"line": STATEMENTS[loc], "english": ENGLISH, "locale": loc, "own": True}
    return {"line": ENGLISH, "english": ENGLISH, "locale": "en-US", "own": False}
