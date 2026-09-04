import os
import logging
import threading
import asyncio
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


# =========================================================
# IRCE COACHING - AI STUDY ASSISTANT
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")


# =========================================================
# GEMINI CLIENT
# =========================================================

client = genai.Client(api_key=GEMINI_API_KEY)

# Primary model + fallback models
MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
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

def run_health_server():

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
# START COMMAND
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = (
        "🎓 *IRCE Coaching में आपका स्वागत है!*\n\n"

        "🤖 मैं आपका AI Study Assistant हूँ।\n\n"

        "📚 किसी command या keyword की जरूरत नहीं है।\n"
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


# =========================================================
# HELP COMMAND
# =========================================================

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

        "आप Notes, MCQ, Explanation और "
        "Question Solving मांग सकते हैं।"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


# =========================================================
# TEMPORARY ERROR CHECK
# =========================================================

def is_temporary_error(error_text: str) -> bool:

    temporary_errors = (
        "503",
        "UNAVAILABLE",
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "INTERNAL",
        "TIMEOUT",
        "DEADLINE_EXCEEDED",
        "timed out",
        "Timeout",
    )

    return any(
        error in error_text
        for error in temporary_errors
    )


# =========================================================
# GEMINI
# =========================================================

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
7. Notes मांगने पर व्यवस्थित Notes दें।
8. MCQ मांगने पर प्रश्न और options दें।
9. Question solve करने को कहा जाए तो
   step-by-step समाधान दें।
10. "आसान तरीके से समझाओ" कहा जाए,
    तो बहुत सरल भाषा का प्रयोग करें।
11. महत्वपूर्ण परीक्षा बिंदुओं को अलग से बताएं।
12. बिना जरूरत बहुत लंबा उत्तर न दें।
13. गलत जानकारी को तथ्य के रूप में प्रस्तुत न करें।
14. उत्तर साफ, उपयोगी और विद्यार्थी-केंद्रित रखें।
15. विद्यार्थी को किसी command की जरूरत नहीं है।

आपका नाम:

IRCE Coaching AI Assistant
"""

    prompt = (
        system_prompt
        + "\n\nविद्यार्थी का प्रश्न:\n"
        + question
    )

    for model_index, model in enumerate(MODELS):

        logger.info(
            "Trying Gemini model: %s (%s/%s)",
            model,
            model_index + 1,
            len(MODELS)
        )

        for attempt in range(2):

            try:

                logger.info(
                    "Gemini request: model=%s attempt=%s/2",
                    model,
                    attempt + 1
                )

                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=prompt
                )

                answer = response.text

                if answer:

                    logger.info(
                        "Gemini response received from %s",
                        model
                    )

                    return answer.strip()

                logger.warning(
                    "Gemini returned empty response: %s",
                    model
                )

            except Exception as e:

                error_text = str(e)

                logger.error(
                    "Gemini error | model=%s | attempt=%s/2 | %s",
                    model,
                    attempt + 1,
                    error_text
                )

                if is_temporary_error(error_text):

                    if attempt == 0:

                        logger.info(
                            "Temporary error. Retrying after 2 seconds..."
                        )

                        await asyncio.sleep(2)

                        continue

                    logger.warning(
                        "Model %s unavailable. Trying next model.",
                        model
                    )

                    break

                else:

                    logger.error(
                        "Non-temporary error. Trying next model."
                    )

                    break


    logger.error("All Gemini models failed.")

    return (
        "⚠️ अभी AI सेवा से उत्तर प्राप्त नहीं हो पाया।\n\n"
        "कृपया कुछ सेकंड बाद वही सवाल फिर से भेजें।"
    )


# =========================================================
# NORMAL MESSAGE
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


# =========================================================
# TELEGRAM ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Telegram Error: %s",
        context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print("======================================")
    print("IRCE Coaching Bot Starting...")
    print("======================================")

    # Render health server
    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
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


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
