"""
Interlinear PDF Translator - Telegram Bot (Cloud & Local Edition)
- High-Speed Serverless & Background Telegram Bot Engine
- Embedded HTTP Health-Check Server (Compatible with Hugging Face, Render, Koyeb, Railway)
- Inline buttons for font size, medical term highlighting, and color customization
- Automatic file download, processing with Turbo Parallel Translator, and instant reply
- Clean file cleanup and robust error handling
"""

import os
import sys
import time
import shutil
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from translator_core import PDFInterlinearTranslator

# Read Bot Token from Environment variable or CLI
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

# User Settings Store (in-memory per chat_id)
USER_SETTINGS = {}

COLOR_OPTIONS = {
    "blue": {"tuple": (0.08, 0.35, 0.78), "label": "🔵 أزرق ملكي"},
    "black": {"tuple": (0.0, 0.0, 0.0), "label": "⚫ أسود"},
    "slate": {"tuple": (0.22, 0.28, 0.35), "label": "🔘 كحلي هادئ"},
    "red": {"tuple": (0.75, 0.12, 0.12), "label": "🔴 أحمر"}
}


class HealthServerHandler(BaseHTTPRequestHandler):
    """Responds to cloud container health checks (Render, Hugging Face, etc.)"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Interlinear PDF Translator Telegram Bot is ONLINE 24/7!")

    def log_message(self, format, *args):
        pass  # Quiet logging


def start_health_server():
    port = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 7860)))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthServerHandler)
        print(f"Health check HTTP server listening on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"Health server warning: {e}")


def get_user_settings(chat_id):
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {
            "font_size": 6.2,
            "highlight_medical": True,
            "color": (0.08, 0.35, 0.78),
            "color_name": "أزرق ملكي"
        }
    return USER_SETTINGS[chat_id]


def build_settings_keyboard(chat_id):
    cfg = get_user_settings(chat_id)
    kb = InlineKeyboardMarkup(row_width=2)

    sz_btn = InlineKeyboardButton(
        f"📏 حجم الخط: {cfg['font_size']} pt",
        callback_data="toggle_size"
    )
    med_status = "🟢 مفعل" if cfg["highlight_medical"] else "⚪ معطل"
    med_btn = InlineKeyboardButton(
        f"🩺 تظليل المصطلحات الطبية: {med_status}",
        callback_data="toggle_medical"
    )
    col_btn = InlineKeyboardButton(
        f"🎨 اللون: {cfg['color_name']}",
        callback_data="toggle_color"
    )

    kb.add(sz_btn)
    kb.add(med_btn)
    kb.add(col_btn)
    return kb


def create_bot(token=None):
    tok = token or BOT_TOKEN
    if not tok:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")
    return telebot.TeleBot(tok, parse_mode="HTML")


def setup_handlers(bot):

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message):
        chat_id = message.chat.id
        welcome_text = (
            "👋 <b>أهلاً بك في بوت الترجمة البينية الاحترافية لملفات الـ PDF!</b>\n\n"
            "✨ <b>مميزات البوت:</b>\n"
            "• ترجمة بينية تضع المعنى العربي مباشرة فوق كل سطر إنجليزي.\n"
            "• تظليل الكلمات والمصطلحات الطبية التخصصية حصراً بالأخضر الزمردي.\n"
            "• معالجة تفرعية فائقة السرعة بدون إسقاط أي سطر.\n\n"
            "⚙️ <b>إعداداتك الحالية أدناه، يمكنك تعديلها أو إرسال أي ملف PDF فوراً لبدء ترجمته:</b>"
        )
        bot.send_message(
            chat_id,
            welcome_text,
            reply_markup=build_settings_keyboard(chat_id)
        )

    @bot.message_handler(commands=["settings"])
    def show_settings(message):
        chat_id = message.chat.id
        bot.send_message(
            chat_id,
            "⚙️ <b>لوحة التحكم بإعدادات الترجمة:</b>",
            reply_markup=build_settings_keyboard(chat_id)
        )

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        chat_id = call.message.chat.id
        cfg = get_user_settings(chat_id)

        if call.data == "toggle_size":
            sizes = [5.0, 5.8, 6.2, 7.0, 8.0]
            cur_idx = sizes.index(cfg["font_size"]) if cfg["font_size"] in sizes else 2
            next_sz = sizes[(cur_idx + 1) % len(sizes)]
            cfg["font_size"] = next_sz
            bot.answer_callback_query(call.id, f"تم تغيير حجم الخط إلى: {next_sz} pt")

        elif call.data == "toggle_medical":
            cfg["highlight_medical"] = not cfg["highlight_medical"]
            status_txt = "مفعل 🟢" if cfg["highlight_medical"] else "معطل ⚪"
            bot.answer_callback_query(call.id, f"تظليل المصطلحات الطبية: {status_txt}")

        elif call.data == "toggle_color":
            color_keys = list(COLOR_OPTIONS.keys())
            cur_key = "blue"
            for k, v in COLOR_OPTIONS.items():
                if v["label"] == cfg["color_name"]:
                    cur_key = k
                    break
            next_key = color_keys[(color_keys.index(cur_key) + 1) % len(color_keys)]
            cfg["color"] = COLOR_OPTIONS[next_key]["tuple"]
            cfg["color_name"] = COLOR_OPTIONS[next_key]["label"]
            bot.answer_callback_query(call.id, f"تم تغيير اللون إلى: {cfg['color_name']}")

        bot.edit_message_reply_markup(
            chat_id,
            call.message.message_id,
            reply_markup=build_settings_keyboard(chat_id)
        )

    @bot.message_handler(content_types=["document"])
    def handle_pdf(message):
        doc = message.document
        if not doc.file_name.lower().endswith(".pdf"):
            bot.reply_to(message, "⚠️ يرجى إرسال ملف بصيغة PDF فقط.")
            return

        chat_id = message.chat.id
        cfg = get_user_settings(chat_id)

        status_msg = bot.reply_to(
            message,
            f"📥 <b>جاري استلام الملف:</b> <code>{doc.file_name}</code>\n"
            f"⚡ جاري تهيئة محرك الترجمة التفرعية الفائقة..."
        )

        tmp_dir = tempfile.mkdtemp(prefix="interlinear_bot_")
        input_pdf_path = os.path.join(tmp_dir, doc.file_name)
        output_pdf_path = os.path.join(tmp_dir, f"Translated_{doc.file_name}")

        try:
            # 1. Download file from Telegram
            file_info = bot.get_file(doc.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open(input_pdf_path, "wb") as f:
                f.write(downloaded)

            last_edit_time = [0]

            def progress_callback(cur, total, text):
                now = time.time()
                if now - last_edit_time[0] > 2.0 or cur == total:
                    last_edit_time[0] = now
                    try:
                        bot.edit_message_text(
                            f"⚙️ <b>جاري المعالجة:</b> <code>{doc.file_name}</code>\n"
                            f"📄 الصفحة {cur} من {total}\n"
                            f"<i>{text}</i>",
                            chat_id,
                            status_msg.message_id
                        )
                    except Exception:
                        pass

            # 2. Translate with Turbo Parallel Translator
            translator = PDFInterlinearTranslator(
                input_pdf_path=input_pdf_path,
                output_pdf_path=output_pdf_path,
                font_size=cfg["font_size"],
                color=cfg["color"],
                highlight_medical=cfg["highlight_medical"],
                progress_callback=progress_callback
            )

            t0 = time.time()
            result = translator.process()
            elapsed = time.time() - t0

            # 3. Send back the translated PDF
            caption = (
                f"🎉 <b>اكتملت الترجمة البينية بنجاح!</b>\n\n"
                f"• عدد الصفحات: {result.get('pages', 0)}\n"
                f"• عدد الأسطر المترجمة: {result.get('lines', 0)}\n"
                f"• وقت التنفيذ: {elapsed:.1f} ثانية ⚡\n"
                f"• حجم الخط: {cfg['font_size']} pt | المصطلحات الطبية: {'🟢 مفعلة' if cfg['highlight_medical'] else '⚪ معطلة'}"
            )

            with open(output_pdf_path, "rb") as out_file:
                bot.send_document(
                    chat_id,
                    out_file,
                    caption=caption,
                    reply_to_message_id=message.message_id
                )

            try:
                bot.delete_message(chat_id, status_msg.message_id)
            except Exception:
                pass

        except Exception as e:
            bot.edit_message_text(
                f"❌ <b>حدث خطأ أثناء معالجة الملف:</b>\n<code>{str(e)}</code>",
                chat_id,
                status_msg.message_id
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    token = sys.argv[1] if len(sys.argv) > 1 else BOT_TOKEN
    if not token:
        print("Error: No bot token provided.")
        print("Usage: python bot.py <YOUR_TELEGRAM_BOT_TOKEN>")
        print("Or set the environment variable TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    # Start cloud health-check HTTP server in background thread
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    bot = create_bot(token)
    setup_handlers(bot)

    print("====================================================")
    print(" Interlinear PDF Translator - Telegram Bot is ONLINE ")
    print(" Listening for incoming documents 24/7...")
    print("====================================================")
    bot.infinity_polling(timeout=20, long_polling_timeout=15)


if __name__ == "__main__":
    main()
