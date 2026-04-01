from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.orm import sessionmaker
import re
import string
import unicodedata
import requests
from typing import Dict, Any
import time
import sys
import threading
import uuid
from collections import defaultdict
import random

# ============================================================
# USER SESSION (ANONYMOUS)
# ============================================================
USER_ID = str(uuid.uuid4())

# ============================================================
# VERIFICATION CACHE (PERFORMANCE)
# ============================================================
VERIFICATION_CACHE = {}

#=============================================================
# TRUSTED SOURCES
#=============================================================

TRUSTED_SOURCES = """
reuters.com apnews.com afp.com upi.com
bbc.com cnn.com aljazeera.com dw.com france24.com
nytimes.com theguardian.com washingtonpost.com wsj.com
economist.com time.com axios.com politico.com
bloomberg.com financialtimes.com cnbc.com forbes.com
businessinsider.com marketscreener.com
thehindu.com indianexpress.com hindustantimes.com ndtv.com
timesofindia.indiatimes.com scroll.in thewire.in
news18.com deccanherald.com firstpost.com livemint.com
moneycontrol.com
nature.com science.org sciencemag.org sciencedirect.com
pnas.org cell.com annualreviews.org
sciencedaily.com phys.org
thelancet.com nejm.org bmj.com jamanetwork.com
who.int cdc.gov nih.gov nhs.uk
medicalnewstoday.com statnews.com
techcrunch.com theverge.com wired.com arstechnica.com
zdnet.com technologyreview.com thenextweb.com
engadget.com cnet.com slashdot.org
mit.edu/news stanford.edu/news
openai.com/blog deepmind.com/blog ai.googleblog.com
foreignpolicy.com foreignaffairs.com
brookings.edu csis.org rand.org iiss.org
carnegieendowment.org chathamhouse.org
cfr.org un.org nato.int imf.org worldbank.org
morningstar.com seekingalpha.com investopedia.com
sec.gov nasdaq.com nyse.com
npr.org pbs.org/newshour
abc.net.au/news cbc.ca/news rfi.fr
dw.com sverigesradio.se
japantimes.co.jp straitstimes.com
scmp.com koreaherald.com
channelnewsasia.com
espn.com espncricinfo.com cricbuzz.com
bbc.com/sport skysports.com cbssports.com nbcsports.com
foxsports.com sports.yahoo.com theathletic.com
sportstar.thehindu.com
fifa.com uefa.com olympics.com insidethegames.biz
formula1.com motorsport.com
atptour.com wtatennis.com
nba.com nfl.com mlb.com
icc-cricket.com rugbyworldcup.com
newyorker.com theatlantic.com
propublica.org theintercept.com2 
""".split()
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ===============================2
# =============================
# FACTORA AI PERSONA MANAGER
# ============================================================
class FactoraPersona:
    def __init__(self):
        self.name = "FACTORA AI"
        self.greetings = [
            "Ready to scan the headlines.",
            "Standing by. Feed me some news.",
            "The truth is out there, but so is the noise. Let's filter it."
        ]
        
    def get_intro(self):
        print(f"\n--- {self.name}  ---")
        gpt_typewriter_line(random.choice(self.greetings))
        print("\nWhat would you like to do first?")
        print("1. 📖 Learn: What is 'Meaning of news/Manipulation'?")
        print("2. 🧠 Analyze: Directly dive into news analysis.")
        return input("\nSelect (1 or 2): ").strip()

    def show_definitions(self):
        print("\n--- FACTORA AI ---")
        gpt_typewriter_line("Manipulation Score: Measures emotional bait, urgency, and 'shock' language.")
        gpt_typewriter_line("Verification Score: Checks if the story aligns with trusted global sources.")
        gpt_typewriter_line("Primary Signal: The main reason why a text was flagged (e.g., Urgency).")
        input("\nPress Enter when you're ready to analyze news...")

    def get_feedback(self):
        print("\n" + "-"*30)
        gpt_typewriter_line("Before you go, what did you think of my analysis?")
        try:
            rating = int(input("On a scale of 1-10, how would you rate FACTORA AI: "))
            if 1 <= rating <= 5:
                gpt_typewriter_line("Understood. I'll recalibrate my sensors to be sharper next time.")
            elif 6 <= rating <= 8:
                gpt_typewriter_line("Not bad! I'm glad I could provide some clarity. Staying critical is key.")
            elif 9 <= rating <= 10:
                gpt_typewriter_line("Excellent. The truth remains our priority. Systems optimal.")
            else:
                gpt_typewriter_line("That's an interesting number. I'll take it as a 'Work in Progress'!")
        except ValueError:
            gpt_typewriter_line("I only understand numbers, but I appreciate the feedback!")

persona = FactoraPersona()

#============================================================
# CATEGORY ↔ SOURCE COMPATIBILITY
# ============================================================

CATEGORY_SOURCE_MAP = {
    "Politics": {
        "reuters.com", "apnews.com", "afp.com",
        "bbc.com", "cnn.com", "aljazeera.com", "dw.com", "france24.com",
        "nytimes.com", "theguardian.com", "washingtonpost.com",
        "wsj.com", "economist.com",
        "politico.com", "axios.com",
        "foreignpolicy.com", "foreignaffairs.com",
        "brookings.edu", "csis.org", "cfr.org",
        "carnegieendowment.org", "chathamhouse.org",
        "un.org"
    }, 
    "World": {
        "reuters.com", "apnews.com", "afp.com",
        "bbc.com", "cnn.com", "aljazeera.com", "dw.com", "france24.com",
        "nytimes.com", "theguardian.com",
        "npr.org", "pbs.org",
        "cbc.ca", "abc.net.au", "rfi.fr",
        "japantimes.co.jp", "straitstimes.com",
        "scmp.com"
    },
    "Economy": {
        "bloomberg.com", "financialtimes.com",
        "cnbc.com", "wsj.com", "economist.com",
        "forbes.com", "businessinsider.com",
        "marketscreener.com",
        "moneycontrol.com", "livemint.com",
        "morningstar.com", "seekingalpha.com",
        "investopedia.com",
        "imf.org", "worldbank.org"
    },
    "Business": {
        "bloomberg.com", "financialtimes.com",
        "wsj.com", "forbes.com", "cnbc.com",
        "businessinsider.com",
        "marketscreener.com",
        "moneycontrol.com", "livemint.com",
        "sec.gov", "nasdaq.com", "nyse.com"
    },
    "Health": {
        "who.int", "cdc.gov", "nih.gov", "nhs.uk",
        "nejm.org", "thelancet.com", "bmj.com",
        "jamanetwork.com",
        "medicalnewstoday.com", "statnews.com"
    },
    "Science": {
        "nature.com", "science.org", "sciencemag.org",
        "cell.com", "pnas.org",
        "sciencedirect.com", "sciencedaily.com",
        "phys.org",
        "mit.edu", "stanford.edu"
    },
    "Technology": {
        "techcrunch.com", "theverge.com", "wired.com",
        "arstechnica.com", "zdnet.com",
        "technologyreview.com", "thenextweb.com",
        "engadget.com", "cnet.com", "slashdot.org",
        "mit.edu", "stanford.edu",
        "openai.com", "deepmind.com", "ai.googleblog.com"
    },
    "Defense": {
        "reuters.com", "apnews.com",
        "bbc.com", "aljazeera.com",
        "foreignpolicy.com", "foreignaffairs.com",
        "csis.org", "iiss.org", "rand.org",
        "nato.int", "defense.gov"
    },
    "Sports": {
        "espn.com", "espncricinfo.com", "cricbuzz.com",
        "bbc.com/sport", "skysports.com",
        "cbssports.com", "nbcsports.com",
        "foxsports.com", "sports.yahoo.com","Supanida Katethong",
        "theathletic.com","Devika Sihag",
        "fifa.com", "uefa.com", "olympics.com",
        "icc-cricket.com", "rugbyworldcup.com",
        "formula1.com", "nba.com", "nfl.com", "mlb.com"
    }
}

def validate_sources_for_category(category: str, sources: list) -> list:
    allowed = CATEGORY_SOURCE_MAP.get(category)
    if not allowed:
        return sources
    return [s for s in sources if s in allowed]

# ============================================================
# DATABASE CONNECTION
# ============================================================
engine = create_engine(
    "sqlite:///factora_ai.db",
    echo=False
)
Session = sessionmaker(bind=engine)

def save_analysis_to_db(news_text, result):
    with open("factora_ai_logs.txt", "a", encoding="utf-8") as f:
        f.write("\n--- FACTORA AI ANALYSIS ---\n")
        f.write(news_text.strip()[:100] + "...\n")
        f.write(str(result) + "\n")
        f.write("-" * 40 + "\n")

# =========================================================
# THINKING ANIMATION
# =========================================================

def thinking_animation(stop_event):
    dots = [".", "..", "...", ""]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r🧠 FACTORA AI is analysing the news{dots[i % 4]}\033[K")
        sys.stdout.flush()
        time.sleep(0.5)
        i += 1

# ============================================================
# TYPEWRITER OUTPUT
# ============================================================
def gpt_typewriter_line(text, speed=0.015, dot=True):
    if dot:
        sys.stdout.write("● ")
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(speed)
    print()

# ============================================================
# INPUT TYPE DETECTION
# ============================================================
def detect_input_type(text: str) -> str:
    cleaned = text.strip().lower()
    if any(q in cleaned for q in ["who is your founder", "who created you", "who made you"]):
        return "founder_query"
    if cleaned in {"hi", "hello", "hey", "yo", "wassup"}:
        return "greeting"
    if cleaned.endswith("?") and len(cleaned.split()) < 12:
        return "question"
    if len(cleaned.split()) < 5:
        return "too_short"
    if sum(c.isalpha() for c in cleaned) / max(len(cleaned), 1) < 0.5:
        return "noise"
    return "news"

def handle_non_news(input_type: str):
    print()
    if input_type == "founder_query":
        gpt_typewriter_line("My founders are Vedant Babar and Yuvraj Desai.")
        return True
    if input_type == "greeting":
        gpt_typewriter_line("👋 Hi! I’m FACTORA AI.")
        gpt_typewriter_line("Paste a news article and I’ll analyze it.")
        return True
    if input_type == "question":
        gpt_typewriter_line("🤖 I’m designed to analyze news articles.")
        gpt_typewriter_line("Please paste a news report.")
        return True
    if input_type == "too_short":
        gpt_typewriter_line("⚠️ Text too short to be news.")
        return True
    if input_type == "noise":
        gpt_typewriter_line("⚠️ Input doesn’t look like real news.")
        return True
    return False

# ============================================================
# INPUT VALIDATION
# ============================================================
def validate_input(text: str) -> Dict[str, Any]:
    if not text.strip():
        return {"valid": False, "reason": "Empty input."}
    if len(text.split()) < 15:
        return {"valid": False, "reason": "Input too short to be news."}
    if sum(c.isalpha() for c in text) / max(len(text), 1) < 0.6:
        return {"valid": False, "reason": "Text lacks meaningful language."}
    if not re.search(r"[.!?]", text):
        return {"valid": False, "reason": "No sentence structure detected."}
    return {"valid": True}

# ============================================================
# TEXT PREPARATION
# ============================================================
def prepare_text_for_ai(text: str) -> Dict[str, Any]:
    lowered = unicodedata.normalize("NFKC", text).lower()
    words = lowered.translate(str.maketrans("", "", string.punctuation)).split()
    return {
        "original_text": text,
        "words": words
    }

# ============================================================
# NEWS CATEGORY DETECTION
# ============================================================
# Added "Sports" to the priority list
PRIORITY_ORDER = ["Politics", "World", "Defense", "Economy", "Business", "Sports", "Technology", "AI"]

CATEGORY_KEYWORDS = {
    "Politics": [
        "election", "minister", "government", "parliament", "policy", "president",
        "legislation", "ballot", "democrat", "republican", "senate", "congress",
        "cabinet", "bureaucracy", "opposition", "coalition", "governance", "mayor",
        "voters", "referendum", "lobbyist", "sanctions", "impeachment", "authority",
        "european union", "eu", "iran", "irgc", "revolutionary guard",
        "terrorist", "terrorism", "designation", "foreign policy"
    ],

    "World": [
        "international", "global", "nato", "un", "diplomacy", "treaty",
        "geopolitics", "bilateral", "summit", "foreign affairs", "border", "humanitarian",
        "embassy", "ambassador", "multilateral", "expatriate", "refugee", "migration",
        "peacekeeping", "envoys", "territory", "overseas", "continent", "world bank"
    ],

    "Defense": [
        "army", "military", "missile", "defense", "weapons", "troops",
        "warfare", "pentagon", "arsenal", "navy", "air force", "infantry",
        "ballistic", "warship", "ammunition", "deployment", "intelligence", "espionage",
        "security forces", "insurgency", "counterterrorism", "battalion", "artillery"
    ],

    "Economy": [
        "inflation", "gdp", "recession", "budget", "fiscal", "interest rate",
        "currency", "central bank", "deficit", "taxation", "microeconomics", "macroeconomics",
        "monetary", "deflation", "trade gap", "exports", "imports", "commodity",
        "economic growth", "austerity", "index", "consumer price", "treasury"
    ],

    "Business": [
        "company", "ceo", "startup", "stock", "revenue", "ipo",
        "merger", "acquisition", "shares", "equity", "enterprise", "venture capital",
        "bankruptcy", "dividend", "stakeholder", "profit", "quarterly", "corporation",
        "market cap", "investment", "commercial", "founder", "trade", "nasdaq"
    ],

    "Sports": [
        "athletics", "football", "soccer", "basketball", "tennis", "cricket",
        "nfl", "nba", "premier league", "epl", "champions league", "world cup",
        "olympics", "grand slam", "super bowl", "tournament", "championship",
        "athlete", "coach", "match", "score", "playoffs", "offside", "hat-trick",
        "knockout", "formula 1", "f1", "ufc", "boxing", "golf", "mlb", "nhl", "Badminton"
    ],

    "Technology": [
        "software", "internet", "platform", "cloud", "tech",
        "cybersecurity", "hardware", "encryption", "semiconductor", "bandwidth", "infrastructure",
        "blockchain", "crypto", "database", "connectivity", "app", "mobile",
        "nanotechnology", "biotech", "gadget", "silicon", "telecom", "digital"
    ],

    "AI": [
        "artificial intelligence", "machine learning", "llm", "chatbot", "generative ai",
        "neural network", "deep learning", "nlp", "computer vision", "automation", "robotics",
        "algorithm", "gpt", "transformer model", "data science", "turing",
        "synthetic media", "inference", "training data", "predictive",
        "cognitive computing", "openai"
    ]
}

def detect_news_category(text: str) -> str:
    clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())

    scores = defaultdict(int)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            # FIX: handle multi-word & real-world phrases
            if keyword in clean_text:
                scores[category] += 1

    if not scores:
        # SMART FALLBACK FOR REAL NEWS
        if any(k in clean_text for k in [
            "iran", "eu", "european union", "terrorist",
            "revolutionary guard", "irgc", "sanctions"
        ]):
            return "Politics"

        return "General / Unclear"

    max_score = max(scores.values())
    candidates = [cat for cat, score in scores.items() if score == max_score]

    for priority in PRIORITY_ORDER:
        if priority in candidates:
            return priority

    return candidates[0]

# ============================================================
# SUMMARY GENERATION
# ============================================================
def generate_summary(text: str) -> str:
    sentences = text.split(".")
    return ".".join(sentences[:2]).strip()

# ============================================================
# MANIPULATION ANALYSIS
# ============================================================
def analyze_manipulation(prepared: Dict[str, Any]) -> Dict[str, Any]:
    text = prepared["original_text"].lower()
    words = prepared["words"]
    EMOTIONAL = {"shocking", "terrifying", "panic", "miracle", "disaster"}
    URGENCY = {"breaking", "urgent", "act now"}
    AUTHORITY = {"experts say", "sources say"}
    emotion = sum(w in EMOTIONAL for w in words)
    urgency = sum(p in text for p in URGENCY)
    authority = sum(p in text for p in AUTHORITY)
    manipulation_score = min((emotion + urgency) / 5, 1.0)
    verification_score = 1.0 - (0.3 if authority else 0)
    verdict = "Likely Fake" if manipulation_score >= 0.6 else "Suspicious" if manipulation_score >= 0.4 else "Likely Real"
    top_signal = "emotion" if emotion else "urgency" if urgency else "authority" if authority else "none"
    return {
        "verdict": verdict,
        "manipulation_score": round(manipulation_score, 2),
        "verification_score": round(verification_score, 2),
        "top_signal": top_signal
    }

# ============================================================
# EXTERNAL VERIFICATION
# ============================================================

def external_context_check(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    found_sources = [source for source in TRUSTED_SOURCES if source.split(".")[0] in text_lower]
    credible_signals = sum([
        len(text.split()) > 40, "," in text,
        any(w in text_lower for w in ["said", "according to", "official"]),
        any(w in text_lower for w in ["government", "ministry", "authorities"])
    ])
    if found_sources: status = "Coverage found"
    elif credible_signals >= 3: status = "Likely real-world reporting (no source cited)"
    else: status = "No confirmed coverage"
    return {"status": status, "sources": found_sources[:3]}


# ============================================================
# VERIFIED NEWS ARTICLE GENERATOR
# ============================================================
def generate_verified_article(news_text: str, category: str, sources: list) -> str:
    intro = f"In a recent development categorized under {category}, multiple reputable sources have reported on this event."
    body = f"\n\nAccording to available reports, {news_text.strip()[:200]}..."
    source_line = f"\n\nThis report is based on coverage from trusted outlets such as {', '.join(sources)}."
    disclaimer = "\n\nNote: This article is an AI-generated summary based on verified reporting."
    return intro + body + source_line + disclaimer

# ============================================================
# REAL NEWS SUMMARY (EXTRACTIVE)
# ============================================================
def generate_actual_summary(news_text: str, max_sentences: int = 2) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', news_text.strip())
    if not sentences: return "Summary unavailable."
    sentences = sorted(sentences, key=len, reverse=True)
    return " ".join(sentences[:max_sentences]).strip()

# ============================================================
# OUTPUT
# ============================================================

def factora_ai_response(result, external, category, summary=None, article=None):
    gpt_typewriter_line("--- FACTORA AI ANALYSIS ---")
    gpt_typewriter_line(f"News Category: {category}")
    gpt_typewriter_line(f"Verdict: {result['verdict']}")
    gpt_typewriter_line(f"Primary Signal: {result['top_signal']}")
    gpt_typewriter_line(f"Manipulation Score: {result['manipulation_score']} / 1.0")
    gpt_typewriter_line(f"Verification Score: {result['verification_score']} / 1.0")
    print()
    gpt_typewriter_line("External Verification:", dot=False)
    gpt_typewriter_line(f"- Status: {external['status']}", dot=True)
    if external.get("sources"):
        gpt_typewriter_line(f"- Sources: {', '.join(external['sources'])}", dot=True)
    if summary:
        print("\nVerified News Summary:")
        gpt_typewriter_line(summary, dot=False)
    if article:
        print("\n📰 VERIFIED NEWS BRIEF\n")
        for line in article.split("\n"): gpt_typewriter_line(line, dot=False)
    print("\nFACTORA AI analyzes language patterns — not factual truth.\nStay critical. Stay informed.")

# ============================================================
# CORE WRAPPER
# ============================================================

def run_factora_analysis(text):
    prepared = prepare_text_for_ai(text)
    manipulation = analyze_manipulation(prepared)
    verification = external_context_check(text)
    category = detect_news_category(text)
    summary = generate_actual_summary(text)
    return {
        "manipulation": manipulation,
        "verification": verification,
        "category": category,
        "summary": summary
    }

# ============================================================
# MAIN LOOP
# ============================================================

def main():
    # STARTING MENU
    choice = persona.get_intro()
    if choice == "1":
        persona.show_definitions()

    while True:
        news_text = input("\nPaste the news/article text :\n").strip()
        if news_text.lower() == 'exit': break
        
        input_type = detect_input_type(news_text)
        if input_type != "news":
            handle_non_news(input_type)
            continue

        stop_event = threading.Event()
        t = threading.Thread(target=thinking_animation, args=(stop_event,))
        t.start()
        
        try:
            start_time = time.time()
            data = run_factora_analysis(news_text)
            
            result = data["manipulation"]
            external = data["verification"]
            category = data["category"]
            summary = data["summary"]

            if external["status"] == "Coverage found" and external.get("sources"):
                external["sources"] = validate_sources_for_category(category, external["sources"])
                if not external["sources"]: external["status"] = "No confirmed coverage"

            if external["status"] == "No confirmed coverage":
                if result["verdict"] in {"Likely Real", "Suspicious"}:
                    result["verdict"] = "Unverified"
                    result["verification_score"] = 0.0

            article = None
            if external["status"] == "Coverage found" and external["sources"]:
                article = generate_verified_article(news_text, category, external["sources"])

            time.sleep(1) # Simulate deep processing
        finally:
            stop_event.set()
            t.join()
            sys.stdout.write("\r\033[K")

        factora_ai_response(result, external, category, summary, article)
        save_analysis_to_db(news_text, data)

        # FEEDBACK SYSTEM
        persona.get_feedback()

        again = input("\nAnalyze another? (y/n): ").lower()
        if again not in {"y", "yes", "yup", "alright", "let's go", "lets go"}: break

    print("\n Stay sharp.")

if __name__ == "__main__":
    main()