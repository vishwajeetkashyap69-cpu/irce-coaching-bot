import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai

# =========================
# IRC COACHING BOT
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

# Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Gemini model
MODEL = "gemini-3.7-flash"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🎓 *IRC Coaching में आपका स्वागत है!*\n\n"
        "मैं आपका AI Study Assistant हूँ।\n\n"
        "📚 आप सीधे अपना सवाल लिख सकते हैं।\n"
        "किसी `/study` या keyword की जरूरत नहीं है।\n\n"
        "उदाहरण:\n"
        "• भारत की राजधानी क्या है?\n"
        "• 1857 की क्रांति समझाइए।\n"
        "• कक्षा 10 इतिहास के महत्वपूर्ण प्रश्न बताओ।\n"
        "• प्रकाश का परावर्तन क्या है?\n"
        "• संविधान की प्रस्तावना समझाइए।\n\n"
        "✍️ बस अपना सवाल लिखिए।"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


# =========================
# HELP
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *IRC Coaching Help*\n\n"
        "बस अपना पढ़ाई से जुड़ा सवाल सीधे लिखें।\n\n"
        "आप पूछ सकते हैं:\n"
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
        "कोई special command जरूरी नहीं है।",
        parse_mode="Markdown"
    )


# =========================
# GEMINI RESPONSE
# =========================

async def ask_gemini(question: str) -> str:

    system_prompt = """
आप IRC Coaching के AI Study Assistant हैं।

आपका मुख्य उद्देश्य विद्यार्थियों को पढ़ाई में मदद करना है।

नियम:

1. उत्तर मुख्य रूप से हिंदी में दें।
2. विद्यार्थी जिस भाषा में पूछे, उसी भाषा में सरल उत्तर दें।
3. कठिन विषय को आसान भाषा में समझाएं।
4. जरूरत होने पर उदाहरण दें।
5. History, Geography, Polity, Science, Maths,
   English, GK और competitive exams के प्रश्नों में
   शैक्षणिक और व्यवस्थित उत्तर दें।
6. यदि प्रश्न किसी कक्षा का हो तो उस स्तर के अनुसार समझाएं।
7. जरूरत होने पर:
   - Definition
   - Explanation
   - Examples
   - Important Points
   - Exam Points
   के रूप में उत्तर दें।
8. विद्यार्थी अगर MCQ मांगे तो MCQ बनाएं।
9. विद्यार्थी अगर notes मांगे तो अच्छे notes बनाएं।
10. विद्यार्थी अगर किसी प्रश्न को solve करने को कहे तो
    step-by-step समाधान दें।
11. बिना जरूरत बहुत लंबा उत्तर न दें।
12. गलत जानकारी को तथ्य के रूप में प्रस्तुत न करें।
13. उत्तर पढ़ाई के उद्देश्य से उपयोगी और साफ रखें।

आपका नाम:
IRC Coaching AI Assistant
"""

    prompt = system_prompt + "\n\nविद्यार्थी का प्रश्न:\n" + question

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        answer = response.text

        if not answer:
            return "माफ कीजिए, अभी उत्तर तैयार नहीं हो पाया। कृपया दोबारा पूछें।"

        return answer

    except Exception as e:
        logger.exception("Gemini Error")
        return (
            "⚠️ अभी AI से उत्तर लेने में समस्या हो रही है।\n"
            "कृपया थोड़ी देर बाद दोबारा प्रयास करें।"
        )


# =========================
# NORMAL MESSAGE
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    question = update.message.text

    if not question:
        return

    # Typing indicator
    await update.message.chat.send_action("typing")

    answer = await ask_gemini(question)

    # Telegram message limit protection
    max_length = 4000

    if len(answer) <= max_length:
        await update.message.reply_text(answer)
    else:
        for i in range(0, len(answer), max_length):
            await update.message.reply_text(
                answer[i:i + max_length]
            )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "Telegram Error: %s",
        context.error
    )


# =========================
# MAIN
# =========================

def main():

    print("===================================")
    print("IRC Coaching Bot Starting...")
    print("===================================")

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    application.add_error_handler(error_handler)

    print("IRC Coaching Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()
