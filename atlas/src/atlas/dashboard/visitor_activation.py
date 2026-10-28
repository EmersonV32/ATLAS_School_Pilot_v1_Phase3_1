"""Local-only visitor wake phrase and greeting helpers."""

from __future__ import annotations

import re
import unicodedata

from atlas.models.languages import normalize_language_code

# Public, fixed copy: never build this introduction from a visitor profile or
# an LLM prompt. Every language exposed by the admin dashboard has its own text.
_INTRODUCTIONS = {
    "en": (
        "Hello, I'm ATLAS, your AI art guide. Ask me about an artwork by name, "
        "or tell me what you would like to explore."
    ),
    "fr": (
        "Bonjour, je suis ATLAS, votre guide artistique virtuel. Posez-moi une "
        "question sur une œuvre en donnant son nom, ou dites-moi ce que vous "
        "souhaitez découvrir."
    ),
    "es": (
        "Hola, soy ATLAS, tu guía de arte con inteligencia artificial. "
        "Pregúntame por una obra diciendo su nombre, o dime qué te gustaría descubrir."
    ),
    "zh": (
        "你好，我是 ATLAS，你的人工智慧藝術導覽員。"
        "請說出作品名稱並向我提問，或告訴我你想探索什麼。"
    ),
    "pt": (
        "Olá, sou o ATLAS, seu guia de arte com inteligência artificial. "
        "Pergunte sobre uma obra dizendo o nome dela, "
        "ou conte o que gostaria de explorar."
    ),
    "ar": (
        "مرحباً، أنا أطلس، دليلك الفني بالذكاء الاصطناعي. "
        "اسألني عن عمل فني بذكر اسمه، أو أخبرني بما تود استكشافه."
    ),
    "hi": (
        "नमस्ते, मैं एटलस हूँ, आपका एआई कला मार्गदर्शक। "
        "किसी कलाकृति का नाम लेकर मुझसे पूछें, या बताएं कि आप क्या जानना चाहते हैं।"
    ),
    "de": (
        "Hallo, ich bin ATLAS, dein KI-Kunstführer. Frage mich nach einem "
        "Kunstwerk und nenne seinen Namen, "
        "oder erzähle mir, was du entdecken möchtest."
    ),
    "it": (
        "Ciao, sono ATLAS, la tua guida d'arte con intelligenza artificiale. "
        "Chiedimi di un'opera dicendo il suo nome, "
        "oppure dimmi cosa vorresti scoprire."
    ),
    "ja": (
        "こんにちは。AIアートガイドのアトラスです。"
        "作品の名前を言って質問するか、知りたいことを教えてください。"
    ),
    "ko": (
        "안녕하세요. 저는 인공지능 미술 안내자 아틀라스입니다. "
        "작품 이름을 말하며 질문하거나, 무엇을 알아보고 싶은지 알려 주세요."
    ),
    "ru": (
        "Здравствуйте! Я АТЛАС, ваш художественный гид с искусственным "
        "интеллектом. Назовите произведение и задайте вопрос "
        "или расскажите, что хотите узнать."
    ),
    "bn": (
        "নমস্কার, আমি অ্যাটলাস, আপনার কৃত্রিম বুদ্ধিমত্তার শিল্প নির্দেশক। "
        "শিল্পকর্মের নাম বলে আমাকে প্রশ্ন করুন, অথবা কী জানতে চান বলুন।"
    ),
    "id": (
        "Halo, saya ATLAS, pemandu seni dengan kecerdasan buatan. "
        "Sebutkan nama karya seni dan ajukan pertanyaan, "
        "atau ceritakan apa yang ingin Anda jelajahi."
    ),
    "te": (
        "నమస్కారం, నేను అట్లాస్, మీ కృత్రిమ మేధ కళా మార్గదర్శిని. "
        "కళాకృతి పేరు చెప్పి ప్రశ్న అడగండి, "
        "లేదా మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారో చెప్పండి."
    ),
    "tr": (
        "Merhaba, ben ATLAS, yapay zekâ sanat rehberinizim. "
        "Bir sanat eserinin adını söyleyerek soru sorun "
        "veya neyi keşfetmek istediğinizi anlatın."
    ),
    "vi": (
        "Xin chào, tôi là ATLAS, hướng dẫn viên nghệ thuật AI của bạn. "
        "Hãy nêu tên tác phẩm và đặt câu hỏi, "
        "hoặc cho tôi biết bạn muốn khám phá điều gì."
    ),
    "ta": (
        "வணக்கம், நான் அட்லஸ், உங்கள் செயற்கை நுண்ணறிவு கலை வழிகாட்டி. "
        "கலைப்படைப்பின் பெயரைக் கூறிக் கேள்வி கேளுங்கள், "
        "அல்லது நீங்கள் தெரிந்துகொள்ள விரும்புவதைச் சொல்லுங்கள்."
    ),
    "th": (
        "สวัสดี ฉันคือแอตลาส ผู้นำชมศิลปะด้วยปัญญาประดิษฐ์ของคุณ "
        "บอกชื่อผลงานแล้วถามฉัน หรือบอกว่าคุณอยากสำรวจเรื่องอะไร"
    ),
    "pl": (
        "Cześć, jestem ATLAS, twój przewodnik po sztuce oparty na sztucznej "
        "inteligencji. Podaj nazwę dzieła i zadaj pytanie "
        "lub powiedz, co chcesz odkryć."
    ),
}

_WAKE_PHRASES = ("hey atlas", "bonjour atlas")
# Ordinary questions can still include a familiar address in the selected
# language. Stripping it must never grant permission to introduce ATLAS.
_ADDRESS_PHRASES = {
    "en": ("hello atlas", "hi atlas"),
    "fr": ("salut atlas",),
    "es": ("hola atlas",),
    "it": ("ciao atlas", "salve atlas"),
    "zh": ("你好 atlas", "你好atlas", "哈囉 atlas", "哈啰 atlas"),
}
_HESITATIONS = {"uh", "um", "erm", "er", "euh", "heu", "hmm", "hum", "eh"}

_GREETINGS = {
    "en": ("Hey {name}, I'm ATLAS.", "Hey, I'm ATLAS."),
    "fr": ("Bonjour {name}, je suis ATLAS.", "Bonjour, je suis ATLAS."),
    "es": ("Hola {name}, soy ATLAS.", "Hola, soy ATLAS."),
    "it": ("Ciao {name}, sono ATLAS.", "Ciao, sono ATLAS."),
    "zh": ("你好，{name}，我是 ATLAS。", "你好，我是 ATLAS。"),
}

_INVITATIONS = {
    "en": "Look at an artwork and ask me anything about it.",
    "fr": "Regardez une œuvre et posez-moi toutes vos questions.",
    "es": "Mira una obra y pregúntame lo que quieras sobre ella.",
    "it": "Guarda un'opera e chiedimi quello che vuoi.",
    "zh": "請看向一件藝術品，然後問我任何問題。",
}


def _language_root(language: str) -> str:
    root = str(language or "en").casefold().split("-", 1)[0]
    return root if root in _GREETINGS else "en"


def _normalize_phrase(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"[^\w\u3400-\u9fff]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def wake_phrase_matches(transcript: str, language: str) -> bool:
    """Accept only an exact explicit greeting, regardless of answer language."""
    return _normalize_phrase(transcript) in _WAKE_PHRASES


def is_hesitation_only(text: str) -> bool:
    """A pause/filler is not a visitor question or a request to start speaking."""
    words = _normalize_phrase(text).split()
    return not words or all(word in _HESITATIONS for word in words)


def wake_phrase_remainder(transcript: str, language: str) -> str | None:
    """Strip an optional opening address without authorizing an introduction.

    None means no address was present. Keep the original question's accents
    and wording: normalization must not turn a French question into ASCII or
    drop a question spoken in the same breath as "Hey Atlas".
    """
    text = unicodedata.normalize("NFKC", str(transcript))
    root = _language_root(language)
    for phrase in (*_ADDRESS_PHRASES[root], *_WAKE_PHRASES):
        prefix = r"[\W_]+".join(re.escape(word) for word in phrase.split())
        # Chinese can continue immediately after the Latin wake name.
        boundary = r"(?![A-Za-z0-9_])" if root == "zh" else r"(?!\w)"
        match = re.match(r"^\s*" + prefix + boundary, text, re.IGNORECASE)
        if match is None:
            continue
        remainder = text[match.end():].lstrip(" \t\r\n,.:;!?…—-，。！？：；、")
        return "" if is_hesitation_only(remainder) else remainder.strip()
    return None


def clean_greeting_name(value: str | None) -> str | None:
    """Return a short human name or reject unsafe/unexpected characters."""
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    if len(cleaned) > 40:
        raise ValueError("greeting name must be 40 characters or fewer")
    allowed_punctuation = {" ", "-", "'", "’"}
    if not all(
        unicodedata.category(char).startswith(("L", "M")) or char in allowed_punctuation
        for char in cleaned
    ):
        raise ValueError("greeting name contains unsupported characters")
    return cleaned


def local_greeting(language: str, name: str | None = None) -> str:
    """Build the one-time greeting that must stay on the local Jetson."""
    root = _language_root(language)
    named, anonymous = _GREETINGS[root]
    opening = named.format(name=name) if name else anonymous
    return f"{opening} {_INVITATIONS[root]}"


def session_introduction(language: str, name: str | None = None) -> str:
    """Return public intro text, or one complete strictly local named greeting.

    Callers MUST use private-local TTS when ``name`` is present. Keeping the
    entire named greeting in one synthesis avoids changing voices mid-greeting.
    """
    if name:
        return local_greeting(language, name)
    return _INTRODUCTIONS[normalize_language_code(language)]
