import os
import logging
import threading
import time
import random
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai


# ==================================================
# IRCE COACHING - TELEGRAM AI STUDY BOT
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")


# ==================================================
# GEMINI
# ==================================================

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-3.7-flash"


# ==================================================
# LOGGING
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ==================================================
# RENDER HEALTH SERVER
# ==================================================

def run_server():

    port = int(os.environ.get("PORT", 10000))

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
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


# ==================================================
# START
# ==================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = (
        "🎓 *IRCE Coaching में आपका स्वागत है!*\n\n"
        "🤖 मैं आपका AI Study Assistant हूँ।\n\n"
        "📚 किसी `/study` या keyword की जरूरत नहीं है।\n\n"
        "✍️ बस अपना सवाल सीधे लिखिए।\n\n"
        "उदाहरण:\n"
        "• भारत की राजधानी क्या है?\n"
        "• 1857 की क्रांति समझाइए।\n"
        "• कक्षा 10 इतिहास के notes बनाओ।\n"
        "• संविधान की प्रस्तावना समझाइए।\n"
        "• 20 Science MCQ बनाओ।\n"
        "• इस सवाल को आसान तरीके से solve करो।\n\n"
        "🎯 *IRCE Coaching AI Assistant*"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


# ==================================================
# HELP
# ==================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = (
        "📖 *IRCE Coaching Help*\n\n"
        "बस अपना सवाल सीधे लिखें।\n"
        "किसी command की जरूरत नहीं है।\n\n"
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
        "आप notes, MCQ, explanation और "
        "question solving भी मांग सकते हैं।"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


# ==================================================
# GEMINI RESPONSE WITH RETRY
# ==================================================

async def ask_gemini(question: str) -> str:

    system_prompt = """
आप IRCE Coaching के AI Study Assistant हैं।

आपका मुख्य उद्देश्य विद्यार्थियों को पढ़ाई में मदद करना है।

नियम:

1. उत्तर मुख्य रूप से हिंदी में दें।
2. विद्यार्थी जिस भाषा में प्रश्न पूछे,
   उसी भाषा में उत्तर दें।
3. कठिन विषय को आसान भाषा में समझाएं।
4. जरूरत होने पर उदाहरण दें।
5. History, Geography, Political Science,
   Economics, Science, Mathematics,
   English, GK और Competitive Exams
   के प्रश्नों में व्यवस्थित उत्तर दें।
6. यदि विद्यार्थी कक्षा बताता है,
   तो उसी कक्षा के स्तर के अनुसार समझाएं।
7. Notes मांगने पर व्यवस्थित notes दें।
8. MCQ मांगने पर प्रश्न और options दें।
9. Question solve करने को कहा जाए तो
   step-by-step समाधान दें।
10. अगर विद्यार्थी कहे "आसान तरीके से समझाओ",
    तो बहुत सरल भाषा का प्रयोग करें।
11. महत्वपूर्ण परीक्षा बिंदुओं को अलग से बताएं।
12. बिना जरूरत बहुत लंबा उत्तर न दें।
13. गलत जानकारी को तथ्य के रूप में प्रस्तुत न करें।
14. विद्यार्थी को पढ़ाई के उद्देश्य से
    उपयोगी और साफ उत्तर दें।
15. विद्यार्थी को /study या किसी keyword
    की जरूरत नहीं है।

आपका नाम:

IRCE Coaching AI Assistant
"""

    prompt = (
        system_prompt
        + "\n\nविद्यार्थी का प्रश्न:\n"
        + question
    )

    # 4 attempts
    for attempt in range(4):

        try:

            logger.info(
                "Gemini request attempt %s/4",
                attempt + 1
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            answer = response.text

            if answer:
                logger.info("Gemini response received")
                return answer

            logger.warning(
                "Gemini returned an empty response"
            )

        except Exception as e:

            error_text = str(e)

            logger.exception(
                "Gemini Error on attempt %s/4",
                attempt + 1
            )

            # Retry only temporary server/rate-limit errors
            temporary_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "500" in error_text
                or "INTERNAL" in error_text
            )

            if not temporary_error:
                break

            if attempt < 3:

                delay = (2 ** attempt) + random.uniform(
                    0.5,
                    1.5
                )

                logger.info(
                    "Temporary Gemini error. "
                    "Retrying in %.1f seconds...",
                    delay
                )

                time.sleep(delay)

    return (
        "⚠️ अभी Gemini AI सेवा व्यस्त है।\n\n"
        "मैंने दोबारा प्रयास किया लेकिन अभी उत्तर "
        "नहीं मिल पाया। कृपया कुछ सेकंड बाद "
        "वही सवाल फिर से भेजें।"
    )


# ==================================================
# NORMAL MESSAGE
# ==================================================

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
        await update.message.chat.send_action(
            "typing"
        )
    except Exception:
        pass

    answer = await ask_gemini(question)

    # Telegram message limit
    max_length = 4000

    if len(answer) <= max_length:

        await update.message.reply_text(
            answer
        )

    else:

        for i in range(
            0,
            len(answer),
            max_length
        ):

            await update.message.reply_text(
                answer[i:i + max_length]
            )


# ==================================================
# ERROR HANDLER
# ==================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Telegram Error: %s",
        context.error
    )


# ==================================================
# MAIN
# ==================================================

def main():

    print("======================================")
    print("IRCE Coaching Bot Starting...")
    print("======================================")

    # Render health server
    threading.Thread(
        target=run_server,
        daemon=True
    ).start()

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    application.add_error_handler(
        error_handler
    )

    print("======================================")
    print("IRCE Coaching Bot is LIVE")
    print("======================================")

    application.run_polling(
        drop_pending_updates=True
    )


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":
    main()
