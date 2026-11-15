"""English / Tamil labels for the user-facing screens."""
import streamlit as st

T = {
    "ask_title": {"en": "Ask about Beldex", "ta": "பெல்டெக்ஸ் பற்றி கேளுங்கள்"},
    "ask_sub": {"en": "Answers come only from the Beldex knowledge base, with sources.",
                "ta": "பதில்கள் Beldex அறிவுத் தளத்திலிருந்து மட்டுமே — ஆதாரங்களுடன்."},
    "placeholder": {"en": "Ask anything about BDX, BChat, BelNet, BNS, masternodes…",
                    "ta": "BDX, BChat, BelNet, BNS, masternodes பற்றி கேளுங்கள்…"},
    "sources": {"en": "Sources", "ta": "ஆதாரங்கள்"},
    "how": {"en": "How this answer was made", "ta": "இந்த பதில் எப்படி உருவானது"},
    "thinking": {"en": "Searching the knowledge base…", "ta": "அறிவுத் தளத்தில் தேடுகிறது…"},
    "helpful": {"en": "Helpful", "ta": "உதவியது"},
    "not_helpful": {"en": "Not helpful", "ta": "உதவவில்லை"},
    "try": {"en": "Try one of these", "ta": "இவற்றில் ஒன்றை முயற்சிக்கவும்"},
    "news_title": {"en": "Beldex news & history", "ta": "பெல்டெக்ஸ் செய்திகள் & வரலாறு"},
    "digest": {"en": "This week's digest", "ta": "இந்த வார சுருக்கம்"},
    "all_sources": {"en": "Everything the assistant knows comes from these sources",
                    "ta": "உதவியாளர் அறிந்த அனைத்தும் இந்த ஆதாரங்களிலிருந்து மட்டுமே"},
}

SUGGESTIONS = {
    "en": ["How did Beldex start?", "What do I need to run a masternode?", "What is BNS and how are fees burned?",
           "What happened with the BSC bridge in June 2026?", "Where can I trade BDX?", "What changed in the Obscura hardfork?"],
    "ta": ["பெல்டெக்ஸ் எப்படி தொடங்கியது?", "Masternode இயக்க என்ன தேவை?", "BNS என்றால் என்ன?",
           "ஜூன் 2026 BSC bridge பிரச்சனை என்ன?", "BDX-ஐ எங்கே trade செய்யலாம்?", "Obscura hardfork-இல் என்ன மாறியது?"],
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str) -> str:
    return T[key][lang()]
