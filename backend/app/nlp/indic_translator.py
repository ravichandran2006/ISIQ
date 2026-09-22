import re
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, Tuple, Optional

class IndicTranslator:
    """
    Multilingual Indic Translation Engine for Bureau of Indian Standards Discovery.
    Supports 16 languages (Schedule VIII Indian Languages + English) with zero API keys.
    """
    # Unicode script ranges for Indian languages
    SCRIPT_RANGES = {
        "hi": (0x0900, 0x097F, "Devanagari (Hindi/Marathi/Sanskrit/Nepali/Maithili)"),
        "bn": (0x0980, 0x09FF, "Bengali / Assamese"),
        "pa": (0x0A00, 0x0A7F, "Gurmukhi (Punjabi)"),
        "gu": (0x0A80, 0x0AFF, "Gujarati"),
        "or": (0x0B00, 0x0B7F, "Odia"),
        "ta": (0x0B80, 0x0BFF, "Tamil"),
        "te": (0x0C00, 0x0C7F, "Telugu"),
        "kn": (0x0C80, 0x0CFF, "Kannada"),
        "ml": (0x0D00, 0x0D7F, "Malayalam"),
        "ur": (0x0600, 0x06FF, "Arabic / Urdu")
    }

    LANGUAGE_NAMES = {
        "en": "English",
        "hi": "हिन्दी (Hindi)",
        "ta": "தமிழ் (Tamil)",
        "te": "తెలుగు (Telugu)",
        "kn": "ಕನ್ನಡ (Kannada)",
        "ml": "മലയാളം (Malayalam)",
        "bn": "বাংলা (Bengali)",
        "mr": "मराठी (Marathi)",
        "gu": "ગુજરાતી (Gujarati)",
        "pa": "ਪੰਜਾਬੀ (Punjabi)",
        "or": "ଓଡ଼ିଆ (Odia)",
        "as": "অসমীয়া (Assamese)",
        "ur": "اردو (Urdu)",
        "sa": "संस्कृतम् (Sanskrit)",
        "ne": "नेपाली (Nepali)",
        "mai": "मैथिली (Maithili)"
    }

    # Offline procurement terminology dictionary for instant zero-latency matching
    OFFLINE_VOCABULARY = {
        # Hindi / Devanagari
        "ब्रेड": "bread",
        "रोटी": "bread",
        "प्रोटीन": "protein",
        "बिस्कुट": "biscuits",
        "सीमेंट": "cement",
        "सौर": "solar",
        "इन्वर्टर": "inverter",
        "केबल": "cable",
        "तार": "wire",
        "स्टील": "steel",
        "अस्पताल": "hospital",
        "खरीद": "procurement",
        "आपूर्ति": "supply",
        "निविदा": "tender",
        "अग्निशामक": "fire extinguisher",
        "दूध": "milk",
        "पाउडर": "powder",
        
        # Tamil
        "ரொட்டி": "bread",
        "புரதம்": "protein",
        "பிஸ்கட்": "biscuits",
        "சிமெண்ட்": "cement",
        "சூரிய": "solar",
        "மின்னழுத்த": "voltage",
        "கம்பி": "wire steel",
        "கொள்முதல்": "procurement",
        
        # Telugu
        "రొట్టె": "bread",
        "ప్రోటీన్": "protein",
        "బిస్కెట్లు": "biscuits",
        "సిమెంట్": "cement",
        "సౌర": "solar",
        "కొనుగోలు": "procurement",
        
        # Bengali
        "রুটি": "bread",
        "প্রোটিন": "protein",
        "বিস্কুট": "biscuits",
        "সিমেন্ট": "cement",
        "সৌর": "solar"
    }

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detects if the text is in an Indian script; returns language code."""
        if not text:
            return "en"

        script_counts = {}
        for char in text:
            code = ord(char)
            for lang, (start, end, _) in cls.SCRIPT_RANGES.items():
                if start <= code <= end:
                    script_counts[lang] = script_counts.get(lang, 0) + 1

        if not script_counts:
            return "en"

        # Return language with most script hits
        detected = max(script_counts, key=script_counts.get)
        return detected

    @classmethod
    def is_indic(cls, text: str) -> bool:
        """Returns True if text contains Indic non-Latin script characters."""
        return cls.detect_language(text) != "en"

    @classmethod
    def translate_to_english(cls, text: str, source_lang: Optional[str] = None) -> Tuple[str, str]:
        """
        Translates text to English for searching the Bureau of Indian Standards database.
        Returns: (translated_text, detected_lang_code)
        """
        text_clean = text.strip()
        if not text_clean:
            return "", "en"

        detected_lang = source_lang or cls.detect_language(text_clean)
        if detected_lang == "en":
            return text_clean, "en"

        # 1. Try free translation endpoint
        try:
            encoded_query = urllib.parse.quote(text_clean[:2000])
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={encoded_query}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if payload and payload[0]:
                    translated_chunks = [item[0] for item in payload[0] if item and item[0]]
                    translated = "".join(translated_chunks).strip()
                    if translated:
                        return translated, detected_lang
        except Exception as e:
            print(f"[IndicTranslator] Online translation fallback: {e}")

        # 2. Offline keyword replacement fallback
        words = text_clean.split()
        translated_tokens = []
        for w in words:
            token = cls.OFFLINE_VOCABULARY.get(w, w)
            translated_tokens.append(token)

        return " ".join(translated_tokens), detected_lang

    @classmethod
    def translate_from_english(cls, text: str, target_lang: str) -> str:
        """
        Translates English text (e.g. AI explanation) to an Indic target language.
        """
        if not text or target_lang == "en":
            return text

        try:
            encoded_query = urllib.parse.quote(text[:2000])
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target_lang}&dt=t&q={encoded_query}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if payload and payload[0]:
                    chunks = [item[0] for item in payload[0] if item and item[0]]
                    return "".join(chunks).strip()
        except Exception as e:
            print(f"[IndicTranslator] Error translating to {target_lang}: {e}")

        return text
