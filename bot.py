"""
Interlinear PDF Translator - Telegram Bot (Full Control Edition)
- Comprehensive User Settings: Font Size, Text Color, Medical Highlighting, Alignment
- Persistent JSON Settings Storage (Per-user persistent configuration)
- Visual Inline Buttons with Active Checkmarks (✅)
- Integrated Cloud Health-Check Server (Port 7860/PORT)
- High-Speed Turbo Parallel Translation Engine
"""

import os
import sys
import time
import json
import shutil
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from translator_core import PDFInterlinearTranslator

# Bot Token from environment or CLI argument
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

# Path for persistent user settings
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")
_settings_lock = threading.Lock()


def load_all_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_user_setting(user_id_str, settings_dict):
    with _settings_lock:
        all_s = load_all_settings()
        all_s[user_id_str] = settings_dict
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(all_s, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


AVAILABLE_SIZES = [
    ("auto", "تلقائي"),
    ("4.5", "4.5"),
    ("5.5", "5.5"),
    ("6.5", "6.5"),
    ("7.5", "7.5"),
    ("8.5", "8.5"),
    ("10.0", "10.0")
]

AVAILABLE_COLORS = {
    "blue": {"tuple": (0.08, 0.35, 0.78), "label": "🔵 أزرق ملكي"},
    "red": {"tuple": (0.75, 0.12, 0.12), "label": "🔴 أحمر طبي"},
    "black": {"tuple": (0.0, 0.0, 0.0), "label": "⚫ أسود كلاسيكي"},
    "green": {"tuple": (0.08, 0.55, 0.25), "label": "🟢 أخضر غامق"},
    "slate": {"tuple": (0.22, 0.28, 0.35), "label": "🔘 كحلي هادئ"}
}

DEFAULT_USER_CONFIG = {
    "font_size_str": "6.5",
    "font_size": 6.5,
    "color_key": "blue",
    "color_tuple": (0.08, 0.35, 0.78),
    "color_label": "🔵 أزرق ملكي",
    "highlight_medical": True,
    "alignment": "balanced_right"
}


def get_user_config(user_id):
    uid_str = str(user_id)
    all_s = load_all_settings()
    if uid_str in all_s:
        cfg = all_s[uid_str]
        # Ensure complete fields
        for k, v in DEFAULT_USER_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    return dict(DEFAULT_USER_CONFIG)


def update_user_config(user_id, updates):
    cfg = get_user_config(user_id)
    cfg.update(updates)
    save_user_setting(str(user_id), cfg)
    return cfg


def build_settings_keyboard(user_id):
    cfg = get_user_config(user_id)
    kb = InlineKeyboardMarkup(row_width=3)

    # 1. Header: Font Size
    kb.add(InlineKeyboardButton("── 📏 حجم الخط (Font Size) ──", callback_data="noop"))
    size_btns = []
    for s_val, s_label in AVAILABLE_SIZES:
        is_active = (cfg["font_size_str"] == s_val)
        btn_text = f"✅ {s_label}" if is_active else s_label
        size_btns.append(InlineKeyboardButton(btn_text, callback_data=f"set_size:{s_val}"))
    # Add in rows of 3 or 4
    for i in range(0, len(size_btns), 4):
        kb.row(*size_btns[i:i + 4])

    # 2. Header: Color
    kb.add(InlineKeyboardButton("── 🎨 لون الترجمة (Text Color) ──", callback_data="noop"))
    col_btns = []
    for c_key, c_info in AVAILABLE_COLORS.items():
        is_active = (cfg["color_key"] == c_key)
        btn_text = f"✅ {c_info['label']}" if is_active else c_info["label"]
        col_btns.append(InlineKeyboardButton(btn_text, callback_data=f"set_color:{c_key}"))
    kb.row(*col_btns[:2])
    kb.row(*col_btns[2:4])
    kb.row(*col_btns[4:])

    # 3. Medical Highlighting Toggle
    med_status = "🟢 مفعل (أخضر زمردي)" if cfg["highlight_medical"] else "⚪ معطل (نفس لون النص)"
    kb.add(InlineKeyboardButton(f"🩺 تظليل المصطلحات الطبية: {med_status}", callback_data="toggle_med"))

    return kb


class HealthServerHandler(BaseHTTPRequestHandler):
    """Responds to cloud container health checks (Render, Hugging Face, etc.)"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Interlinear PDF Translator Telegram Bot is ONLINE 24/7!")

    def log_message(self, format, *args):
        pass


def start_health_server():
    port = int(os.environ.get("PORT", os.environ.get("SERVER_PORT", 7860)))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthServerHandler)
        print(f"Health check HTTP server listening on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"Health server note: {e}")


def create_bot(token=None):
    tok = token or BOT_TOKEN
    if not tok:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")
    return telebot.TeleBot(tok, parse_mode="HTML")


def setup_handlers(bot):

    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message):
        user_id = message.from_user.id
        cfg = get_user_config(user_id)
        welcome_text = (
            "👋 <b>مرحباً بك في بوت الترجمة البينية لملفات الـ PDF!</b>\n\n"
            "✨ <b>مميزات البوت:</b>\n"
            "• ترجمة سطرية دقيقة تضع المعنى العربي مباشرة فوق كل سطر إنجليزي.\n"
            "• تظليل الكلمات والمصطلحات الطبية حصراً باللون الأخضر الزمردي الهادئ.\n"
            "• محاذاة متوازنة وتحكم فوري وكامل بحجم الخط ولون النص.\n\n"
            f"⚙️ <b>إعداداتك المحفوظة حالياً:</b>\n"
            f"• حجم الخط: <b>{cfg['font_size_str']} pt</b>\n"
            f"• اللون: <b>{cfg['color_label']}</b>\n"
            f"• التظليل الطبي: <b>{'🟢 مفعل' if cfg['highlight_medical'] else '⚪ معطل'}</b>\n\n"
            "👇 <b>اضغط على الأزرار أدناه لتغيير الحجم أو اللون في أي وقت، أو أرسل ملف PDF للترجمة فوراً:</b>"
        )
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=build_settings_keyboard(user_id)
        )

    @bot.message_handler(commands=["settings"])
    def show_settings(message):
        user_id = message.from_user.id
        bot.send_message(
            message.chat.id,
            "⚙️ <b>لوحة التحكم بإعدادات الخط والألوان:</b>",
            reply_markup=build_settings_keyboard(user_id)
        )

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        user_id = call.from_user.id
        data = call.data

        if data == "noop":
            bot.answer_callback_query(call.id)
            return

        cfg = get_user_config(user_id)

        if data.startswith("set_size:"):
            s_val = data.split(":", 1)[1]
            real_size = None if s_val == "auto" else float(s_val)
            update_user_config(user_id, {
                "font_size_str": s_val,
                "font_size": real_size
            })
            bot.answer_callback_query(call.id, f"✅ تم تثبيت حجم الخط: {s_val} pt")

        elif data.startswith("set_color:"):
            c_key = data.split(":", 1)[1]
            if c_key in AVAILABLE_COLORS:
                c_info = AVAILABLE_COLORS[c_key]
                update_user_config(user_id, {
                    "color_key": c_key,
                    "color_tuple": c_info["tuple"],
                    "color_label": c_info["label"]
                })
                bot.answer_callback_query(call.id, f"✅ تم تثبيت اللون: {c_info['label']}")

        elif data == "toggle_med":
            new_status = not cfg["highlight_medical"]
            update_user_config(user_id, {"highlight_medical": new_status})
            txt = "مفعل 🟢" if new_status else "معطل ⚪"
            bot.answer_callback_query(call.id, f"تظليل المصطلحات الطبية: {txt}")

        try:
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=build_settings_keyboard(user_id)
            )
        except Exception:
            pass

    @bot.message_handler(content_types=["document"])
    def handle_pdf(message):
        doc = message.document
        if not doc.file_name.lower().endswith(".pdf"):
            bot.reply_to(message, "⚠️ يرجى إرسال ملف بصيغة PDF فقط.")
            return

        user_id = message.from_user.id
        chat_id = message.chat.id
        cfg = get_user_config(user_id)

        sz_display = "تلقائي" if cfg["font_size"] is None else f"{cfg['font_size']} pt"
        med_display = "🟢 مفعل" if cfg["highlight_medical"] else "⚪ معطل"

        status_msg = bot.reply_to(
            message,
            f"📥 <b>تم استلام الملف:</b> <code>{doc.file_name}</code>\n"
            f"⚙️ <b>الإعدادات المطبقة:</b> خط {sz_display} | {cfg['color_label']} | طبي {med_display}\n"
            f"⚡ جاري المعالجة بالترجمة التفرعية الفائقة..."
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
                            f"⚙️ <b>جاري ترجمة:</b> <code>{doc.file_name}</code>\n"
                            f"📄 الصفحة {cur} من {total}\n"
                            f"<i>{text}</i>",
                            chat_id,
                            status_msg.message_id
                        )
                    except Exception:
                        pass

            # 2. Run Translator with User Config
            translator = PDFInterlinearTranslator(
                input_pdf_path=input_pdf_path,
                output_pdf_path=output_pdf_path,
                font_size=cfg["font_size"],
                color=cfg["color_tuple"],
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
                f"• حجم الخط: {sz_display} | اللون: {cfg['color_label']}"
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
