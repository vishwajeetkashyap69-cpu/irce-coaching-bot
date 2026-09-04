import os
import logging
import re
from html import escape
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from groq import Groq


# =========================================================
# IRCE COACHING - FAST & ATTRACTIVE AI STUDY BOT
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing")


# =========================================================
# GROQ CLIENT - FREE AI
# =========================================================

groq_client = Groq(api_key=GROQ_API_KEY)

# Fast free models
PRIMARY_MODEL = "openai/gpt-oss-120b"

FALLBACK_MODELS = [
    "openai/gpt-oss-20b",
]


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

def run_server():
    port = int(os.environ.get("PORT", 10000))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )
            self.end_headers()
            self.wfile.write(
                b"IRCE Coaching Bot is running"
            )

        def log_message(self, format, *args):
            return

    server = HTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(f"Health server running on port {port}")
    server.serve_forever()


# =========================================================
# TELEGRAM SAFE REPLY
# =========================================================

async def safe_reply(message, text):
    try:
        await message.reply_text(text)
        return True

    except (TimedOut, NetworkError) as e:
        logger.warning("Telegram network error: %s", e)
        return False

    except Exception as e:
        logger.error("Telegram reply error: %s", e)
        return False


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    message = (
        "🎓 IRCE Coaching में आपका स्वागत है!\n\n"
        "🤖 मैं आपका AI Study Assistant हूँ।\n\n"
        "📚 किसी command या keyword की जरूरत नहीं है।\n"
        "✍️ बस अपना सवाल सीधे लिखिए।\n\n"
        "उदाहरण:\n\n"
        "🇮🇳 भारत की राजधानी क्या है?\n"
        "📖 1857 की क्रांति समझाइए।\n"
        "📝 कक्षा 10 इतिहास के notes बनाओ।\n"
        "🏛️ संविधान की प्रस्तावना समझाइए।\n"
        "❓ 20 Science MCQ बनाओ।\n"
        "➗ इस सवाल को आसान तरीके से solve करो।\n"
        "📚 50 GK MCQ बनाओ।\n"
        "📝 कक्षा 10 विज्ञान के notes बनाओ।\n\n"
        "🎯 IRCE Coaching AI Assistant"
    )

    await safe_reply(update.message, message)


# =========================================================
# HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    message = (
        "📖 IRCE Coaching Help\n\n"
        "बस अपना सवाल सीधे लिखें।\n\n"
        "📚 History\n"
        "🌍 Geography\n"
        "🏛️ Political Science\n"
        "💰 Economics\n"
        "🔬 Science\n"
        "➗ Mathematics\n"
        "🇬🇧 English\n"
        "🧠 Reasoning\n"
        "🌐 GK\n"
        "🎯 Competitive Exams\n\n"
        "आप Notes, MCQ, Explanation और "
        "Question Solving मांग सकते हैं।\n\n"
        "Quick commands (optional):\n"
        "/mcq 20 कक्षा 10 इतिहास\n"
        "/notes कक्षा 10 इतिहास अध्याय 1"
    )

    await safe_reply(update.message, message)


# =========================================================
# TEMPORARY GROQ ERROR CHECK
# =========================================================

def is_temporary_error(error_text):
    error_text = error_text.upper()

    temporary_errors = (
        "429",
        "RATE_LIMIT",
        "TOO MANY REQUESTS",
        "503",
        "UNAVAILABLE",
        "500",
        "INTERNAL",
        "TIMEOUT",
        "TIMED OUT",
        "SERVICE UNAVAILABLE",
    )

    return any(
        error in error_text
        for error in temporary_errors
    )


# =========================================================
# GROQ AI
# =========================================================

def clean_ai_text(text):
    if not text:
        return ""

    # Normalize escaped Markdown characters.
    text = text.replace(r"\*", "*")
    text = text.replace(r"\_", "_")
    text = text.replace(r"\[", "[")
    text = text.replace(r"\]", "]")
    text = text.replace(r"\(", "(")
    text = text.replace(r"\)", ")")
    text = text.replace(r"\#", "#")

    # Remove Markdown images/links, keeping visible text.
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Remove Telegram image URLs.
    text = re.sub(
        r'https?://web\.telegram\.org/\S+',
        '',
        text,
        flags=re.IGNORECASE,
    )

    # Convert bold/italic Markdown to plain text.
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = re.sub(r'\*([^*\n]+)\*', r'\1', text)

    # Remove heading markers and backticks.
    text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)
    text = text.replace("`", "")

    # Convert list bullets to a simple dash.
    text = re.sub(
        r'^\s*[•*🔹👉]\s+',
        '- ',
        text,
        flags=re.MULTILINE,
    )

    # If a line was intended as a bold/list item but has no dash,
    # leave it as normal text; no bold formatting is used anywhere.
    text = re.sub(r'\[([^\]]+)\]', r'\1', text)

    # Clean spacing.
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def detect_request_mode(question):
    """Detect the student's likely request type without another AI call."""
    q = question.lower().strip()

    # MCQ / objective practice
    mcq_words = (
        "mcq", "m.c.q", "multiple choice", "objective",
        "बहुविकल्प", "बहुविकल्पीय", "ऑब्जेक्टिव", "वस्तुनिष्ठ",
        "प्रश्न बनाओ", "प्रश्न दो", "questions"
    )
    if any(word in q for word in mcq_words):
        return "MCQ"

    # Notes / revision
    notes_words = (
        "notes", "note", "नोट्स", "नोट", "short notes",
        "संक्षिप्त नोट्स", "रिवीजन", "revision", "पढ़ने की सामग्री"
    )
    if any(word in q for word in notes_words):
        return "NOTES"

    # Solving / explanation
    solve_words = (
        "solve", "solution", "हल करो", "हल करें", "समाधान",
        "explain", "explanation", "समझाओ", "समझाइए", "बताओ",
        "कैसे", "क्यों", "what is", "meaning"
    )
    if any(word in q for word in solve_words):
        return "EXPLANATION"

    return "GENERAL"


def detect_question_count(question):
    """Find a requested MCQ/question count; default to 10."""
    match = re.search(r"(?<!\d)(\d{1,3})(?!\d)\s*(?:mcq|m\.c\.q|questions?|प्रश्न|सवाल)", question, re.IGNORECASE)
    if match:
        count = int(match.group(1))
        return max(1, min(count, 100))

    # Also support forms like: 20 Science MCQ
    match = re.search(r"(?<!\d)(\d{1,3})(?!\d)", question)
    if match and detect_request_mode(question) == "MCQ":
        count = int(match.group(1))
        return max(1, min(count, 100))

    return 10


def build_request_instruction(question):
    mode = detect_request_mode(question)

    if mode == "MCQ":
        count = detect_question_count(question)
        return (
            f"REQUEST MODE: MCQ\n"
            f"- विद्यार्थी ने MCQ मांगे हैं। कुल {count} प्रश्न दें।\n"
            "- हर प्रश्न के 4 विकल्प दें: A, B, C, D।\n"
            "- प्रश्न क्रमांक साफ रखें।\n"
            "- अंत में अलग से उत्तर कुंजी दें।\n"
            "- प्रश्न विषय और बताई गई कक्षा/परीक्षा के स्तर के अनुरूप हों।\n"
            "- तथ्यात्मक प्रश्नों में मनगढ़ंत जानकारी न दें।"
        )

    if mode == "NOTES":
        return (
            "REQUEST MODE: NOTES\n"
            "- विद्यार्थी को व्यवस्थित परीक्षा-उपयोगी नोट्स दें।\n"
            "- पहले विषय/अध्याय का नाम, फिर परिचय, मुख्य बिंदु, महत्वपूर्ण तथ्य और परीक्षा में याद रखने योग्य बातें दें।\n"
            "- यदि कक्षा बताई गई है तो उसी स्तर की भाषा रखें।\n"
            "- अनावश्यक लंबी भूमिका न दें।"
        )

    if mode == "EXPLANATION":
        return (
            "REQUEST MODE: EXPLANATION\n"
            "- विद्यार्थी की बात को आसान भाषा में समझाएं।\n"
            "- जरूरत होने पर चरणबद्ध तरीके से समझाएं।\n"
            "- अंत में छोटा परीक्षा-उपयोगी निष्कर्ष दें।"
        )

    return (
        "REQUEST MODE: GENERAL\n"
        "- विद्यार्थी के सीधे प्रश्न का सीधा, सही और उपयोगी उत्तर दें।"
    )


async def ask_groq(question):
    system_prompt = """
आप IRCE Coaching के AI Study Assistant हैं।

आपका काम विद्यार्थियों को तेज, सही, सरल और आकर्षक तरीके से पढ़ाई में मदद करना है।

भाषा:
1. विद्यार्थी जिस भाषा में प्रश्न पूछे, उसी भाषा में उत्तर दें।
2. हिंदी प्रश्नों का उत्तर सरल और स्वाभाविक हिंदी में दें।
3. कठिन विषय को विद्यार्थी के स्तर के अनुसार आसान भाषा में समझाएं।
4. यदि विद्यार्थी कक्षा बताता है, तो उसी कक्षा के स्तर के अनुसार उत्तर दें।

Formatting:
1. Bold formatting बिल्कुल न करें। महत्वपूर्ण points के लिए केवल - (dash) का उपयोग करें।
2. Markdown links, image links और web.telegram.org URLs बिल्कुल न दें।
3. Heading के लिए emoji और साफ text का उपयोग करें।
4. उत्तर मोबाइल पर पढ़ने में आसान होना चाहिए।
5. महत्वपूर्ण बातों के लिए 🔹 या 👉 का उपयोग करें।
6. अनावश्यक website links या image URLs न दें।

Heading के उदाहरण:

🇮🇳 भारत की राजधानी

📚 परीक्षा के लिए महत्वपूर्ण तथ्य

📝 संक्षिप्त नोट्स

🎯 परीक्षा में याद रखें

❓ महत्वपूर्ण प्रश्न

Notes मांगने पर:

📝 विषय का नाम

🔹 परिचय
🔹 मुख्य बिंदु
🔹 महत्वपूर्ण तथ्य
🔹 परीक्षा के लिए महत्वपूर्ण बातें

🎯 याद रखने योग्य तथ्य

MCQ मांगने पर:

❓ प्रश्न 1

A. पहला विकल्प
B. दूसरा विकल्प
C. तीसरा विकल्प
D. चौथा विकल्प

✅ उत्तर: B

Question solving के लिए:

🧩 समाधान

चरण 1:
...

चरण 2:
...

चरण 3:
...

✅ अंतिम उत्तर:
...

महत्वपूर्ण नियम:
1. उत्तर सीधा और उपयोगी रखें।
2. अनावश्यक भूमिका न लिखें।
3. बिना जरूरत बहुत लंबा उत्तर न दें।
4. तथ्यात्मक जानकारी में सावधानी रखें।
5. अनुमान को तथ्य की तरह प्रस्तुत न करें।
6. विद्यार्थी को /study command की जरूरत नहीं है।
7. अंत में "अगर आपको और जानकारी चाहिए..." जैसी अनावश्यक लाइन न लिखें।
8. हर उत्तर को साफ, आकर्षक और व्यवस्थित रखें।
9. प्रश्न के अनुसार ही sections इस्तेमाल करें।
10. परीक्षा से जुड़े प्रश्नों में महत्वपूर्ण वर्ष, नाम और तथ्य साफ तरीके से बताएं।

आपका नाम:
IRCE Coaching AI Assistant
"""

    request_instruction = build_request_instruction(question)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": request_instruction + "\n\nSTUDENT QUESTION:\n" + question,
        },
    ]

    # Primary model: one request first for speed.
    try:
        logger.info("Groq primary request: %s", PRIMARY_MODEL)

        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model=PRIMARY_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=1800,
        )

        answer = response.choices[0].message.content

        if answer:
            logger.info("Primary Groq response received")
            return clean_ai_text(answer)

    except Exception as e:
        error_text = str(e)

        logger.warning(
            "Primary Groq error: %s",
            error_text
        )

        if not is_temporary_error(error_text):
            return (
                "⚠️ अभी AI से उत्तर प्राप्त नहीं हो पाया।\n\n"
                "कृपया प्रश्न दोबारा भेजें।"
            )

    # One lightweight fallback only.
    for model in FALLBACK_MODELS:
        try:
            logger.info("Trying Groq fallback model: %s", model)

            response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=1800,
            )

            answer = response.choices[0].message.content

            if answer:
                logger.info(
                    "Fallback Groq response received: %s",
                    model
                )
                return clean_ai_text(answer)

        except Exception as e:
            logger.warning(
                "Fallback Groq model %s failed: %s",
                model,
                e
            )

    return (
        "⚠️ अभी AI सेवा थोड़ी व्यस्त है।\n\n"
        "कुछ सेकंड बाद अपना सवाल फिर भेजें।"
    )


# =========================================================
# OPTIONAL QUICK COMMANDS
# =========================================================

async def mcq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    question = " ".join(context.args).strip()
    if not question:
        await safe_reply(update.message, "उदाहरण: /mcq 20 कक्षा 10 इतिहास")
        return
    await update.message.chat.send_action("typing")
    answer = await ask_groq(f"{question} MCQ")
    await send_long_reply(update.message, answer)


async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    question = " ".join(context.args).strip()
    if not question:
        await safe_reply(update.message, "उदाहरण: /notes कक्षा 10 इतिहास अध्याय 1")
        return
    await update.message.chat.send_action("typing")
    answer = await ask_groq(f"{question} के notes बनाओ")
    await send_long_reply(update.message, answer)


async def send_long_reply(message, text):
    max_length = 4000
    if len(text) <= max_length:
        await safe_reply(message, text)
        return

    for i in range(0, len(text), max_length):
        if not await safe_reply(message, text[i:i + max_length]):
            break


# =========================================================
# NORMAL MESSAGE HANDLER
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    question = update.message.text

    if not question:
        return

    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    answer = await ask_groq(question)

    await send_long_reply(update.message, answer)


# =========================================================
# TELEGRAM ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    error = context.error

    if isinstance(error, TimedOut):
        logger.warning("Telegram request timed out.")
        return

    if isinstance(error, NetworkError):
        logger.warning(
            "Telegram network error: %s",
            error
        )
        return

    logger.error(
        "Telegram Error: %s",
        error
    )


# =========================================================
# MAIN
# =========================================================

def main():
    print("======================================")
    print("IRCE Coaching FREE Groq AI Bot Starting...")
    print("======================================")

    # Health server
    threading.Thread(
        target=run_server,
        daemon=True
    ).start()

    # Telegram application
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .get_updates_connect_timeout(30)
        .get_updates_read_timeout(30)
        .get_updates_write_timeout(30)
        .get_updates_pool_timeout(30)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("mcq", mcq_command)
    )

    application.add_handler(
        CommandHandler("notes", notes_command)
    )

    # Normal text messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    # Error handler
    application.add_error_handler(
        error_handler
    )

    print("======================================")
    print("IRCE Coaching Bot is LIVE")
    print("======================================")

    application.run_polling(
        drop_pending_updates=True,
        poll_interval=0.2,
        timeout=15,
        bootstrap_retries=-1
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
