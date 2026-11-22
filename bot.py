"""
Interlinear PDF Translator - Telegram Bot (Full Control Edition v2.0)
- Persistent JSON Settings Storage (Per-user persistent configuration)
- Permanent ReplyKeyboardMarkup (أزرار ثابتة أسفل الشاشة للتحكم الكامل)
- Visual Inline Keyboards with Active Selection Checkmarks (✅)
- Structured Box Fields for Receipt, Progress, and Delivery (حقول واضحة ومنظمة)
- Embedded Cloud Health-Check Server (Port 7860/PORT)
- Turbo Parallel Translation Engine (8 Workers, High Accuracy)
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
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
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
        except Exception as e:
            print(f"Error saving user settings: {e}")


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
    "red": {"tuple": (0.75, 0.12, 0.12), "label": "🔴 أحمر طبي"},
    "blue": {"tuple": (0.08, 0.35, 0.78), "label": "🔵 أزرق ملكي"},
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
        cfg = dict(all_s[uid_str])
        for k, v in DEFAULT_USER_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        # Ensure color_tuple is a tuple of floats
        if isinstance(cfg.get("color_tuple"), (list, tuple)):
            cfg["color_tuple"] = tuple(float(c) for c in cfg["color_tuple"])
        else:
            cfg["color_tuple"] = DEFAULT_USER_CONFIG["color_tuple"]
        # Ensure font_size is float or None
        if cfg.get("font_size_str") == "auto":
            cfg["font_size"] = None
        elif cfg.get("font_size") is not None:
            cfg["font_size"] = float(cfg["font_size"])
        return cfg
    return dict(DEFAULT_USER_CONFIG)


def update_user_config(user_id, updates):
    cfg = get_user_config(user_id)
    cfg.update(updates)
    save_user_setting(str(user_id), cfg)
    return cfg


def build_persistent_reply_keyboard():
    """Builds the persistent bottom menu that never disappears."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = KeyboardButton("⚙️ لوحة الإعدادات الشاملة")
    b2 = KeyboardButton("📊 فحص إعداداتي الحالية")
    b3 = KeyboardButton("📏 تغيير حجم الخط")
    b4 = KeyboardButton("🎨 تغيير لون الترجمة")
    b5 = KeyboardButton("🩺 تبديل التظليل الطبي")
    b6 = KeyboardButton("🔄 استعادة الافتراضي")
    kb.row(b1)
    kb.row(b3, b4)
    kb.row(b5, b2)
    kb.row(b6)
    return kb


def build_settings_inline_keyboard(user_id):
    """Builds interactive inline keyboard with live checkmarks."""
    cfg = get_user_config(user_id)
    kb = InlineKeyboardMarkup(row_width=3)

    # 1. Header: Font Size
    kb.add(InlineKeyboardButton("── 📏 حجم الخط (Font Size) ──", callback_data="noop"))
    size_btns = []
    for s_val, s_label in AVAILABLE_SIZES:
        is_active = (cfg["font_size_str"] == s_val)
        btn_text = f"✅ {s_label}" if is_active else s_label
        size_btns.append(InlineKeyboardButton(btn_text, callback_data=f"set_size:{s_val}"))
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
    med_status = "🟢 مفعل (زمردي)" if cfg["highlight_medical"] else "⚪ معطل (عادي)"
    kb.add(InlineKeyboardButton(f"🩺 تظليل المصطلحات الطبية: {med_status}", callback_data="toggle_med"))

    return kb


def build_size_inline_keyboard(user_id):
    """Builds inline keyboard focused on font size."""
    cfg = get_user_config(user_id)
    kb = InlineKeyboardMarkup(row_width=4)
    size_btns = []
    for s_val, s_label in AVAILABLE_SIZES:
        is_active = (cfg["font_size_str"] == s_val)
        btn_text = f"✅ {s_label}" if is_active else s_label
        size_btns.append(InlineKeyboardButton(btn_text, callback_data=f"set_size:{s_val}"))
    for i in range(0, len(size_btns), 4):
        kb.row(*size_btns[i:i + 4])
    return kb


def build_color_inline_keyboard(user_id):
    """Builds inline keyboard focused on text colors."""
    cfg = get_user_config(user_id)
    kb = InlineKeyboardMarkup(row_width=2)
    col_btns = []
    for c_key, c_info in AVAILABLE_COLORS.items():
        is_active = (cfg["color_key"] == c_key)
        btn_text = f"✅ {c_info['label']}" if is_active else c_info["label"]
        col_btns.append(InlineKeyboardButton(btn_text, callback_data=f"set_color:{c_key}"))
    kb.row(*col_btns[:2])
    kb.row(*col_btns[2:4])
    kb.row(*col_btns[4:])
    return kb


def format_user_profile_card(cfg):
    """Formats a beautiful, structured text card showing active settings."""
    sz_display = "تلقائي (تناسبي)" if cfg["font_size_str"] == "auto" else f"{cfg['font_size_str']} pt"
    med_display = "🟢 مفعل (أخضر زمردي هادئ)" if cfg["highlight_medical"] else "⚪ معطل (نفس لون الترجمة)"
    card = (
        "╔══════════════════════════════╗\n"
        "║  ⚙️ <b>لوحة إعداداتك المحفوظة</b>          ║\n"
        "╚══════════════════════════════╝\n\n"
        "📋 <b>الحقول المعتمدة لترجمة ملفاتك:</b>\n"
        f"├ 📏 <b>حجم الخط:</b> <code>{sz_display}</code>\n"
        f"├ 🎨 <b>لون الترجمة:</b> <code>{cfg['color_label']}</code>\n"
        f"├ 🩺 <b>تظليل المصطلحات:</b> <code>{med_display}</code>\n"
        "└ 📐 <b>المحاذاة:</b> <code>متوازن لليمين (طبيعي)</code>\n\n"
        "💾 <i>ملاحظة: هذه الإعدادات محفوظة في حسابك دائماً وتُطبّق تلقائياً على كل ملف ترسله.</i>"
    )
    return card


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
        reply_kb = build_persistent_reply_keyboard()

        welcome_text = (
            "👋 <b>أهلاً بك في بوت الترجمة البينية الاحترافي (Interlinear PDF)!</b>\n\n"
            "✨ <b>كيف يعمل البوت؟</b>\n"
            "• يضع الترجمة العربية مباشرة فوق كل سطر إنجليزي في ملف الـ PDF.\n"
            "• يظلل الكلمات والمصطلحات الطبية حصراً باللون الأخضر الزمردي الهادئ.\n"
            "• يحافظ على تنسيق الصور والجداول والصفحات بدقة متناهية.\n\n"
            + format_user_profile_card(cfg) + "\n\n"
            "👇 <b>يمكنك التحكم بالإعدادات من الأزرار السفلية أو الأزرار التفاعلية أدناه:</b>"
        )
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=build_settings_inline_keyboard(user_id)
        )
        # Also ensure persistent menu is active
        bot.send_message(
            message.chat.id,
            "📂 <b>أرسل الآن أي ملف PDF وسأقوم بترجمته فوراً حسب إعداداتك المحفوظة!</b>",
            reply_markup=reply_kb
        )

    @bot.message_handler(commands=["settings"])
    def show_settings_cmd(message):
        user_id = message.from_user.id
        cfg = get_user_config(user_id)
        bot.send_message(
            message.chat.id,
            format_user_profile_card(cfg),
            reply_markup=build_settings_inline_keyboard(user_id)
        )

    # ---------------- Persistent Menu Handlers ---------------- #
    @bot.message_handler(func=lambda msg: msg.text == "⚙️ لوحة الإعدادات الشاملة")
    def on_full_settings_menu(message):
        user_id = message.from_user.id
        cfg = get_user_config(user_id)
        bot.send_message(
            message.chat.id,
            format_user_profile_card(cfg),
            reply_markup=build_settings_inline_keyboard(user_id)
        )

    @bot.message_handler(func=lambda msg: msg.text == "📊 فحص إعداداتي الحالية")
    def on_check_settings_menu(message):
        user_id = message.from_user.id
        cfg = get_user_config(user_id)
        bot.send_message(
            message.chat.id,
            format_user_profile_card(cfg)
        )

    @bot.message_handler(func=lambda msg: msg.text == "📏 تغيير حجم الخط")
    def on_change_size_menu(message):
        user_id = message.from_user.id
        cfg = get_user_config(user_id)
        bot.send_message(
            message.chat.id,
            f"📏 <b>اختر حجم الخط المناسب لترجمتك (الحالي: {cfg['font_size_str']} pt):</b>",
            reply_markup=build_size_inline_keyboard(user_id)
        )

    @bot.message_handler(func=lambda msg: msg.text == "🎨 تغيير لون الترجمة")
    def on_change_color_menu(message):
        user_id = message.from_user.id
        cfg = get_user_config(user_id)
        bot.send_message(
            message.chat.id,
            f"🎨 <b>اختر اللون المفضل لنص الترجمة (الحالي: {cfg['color_label']}):</b>",
            reply_markup=build_color_inline_keyboard(user_id)
        )

    @bot.message_handler(func=lambda msg: msg.text == "🩺 تبديل التظليل الطبي")
    def on_toggle_med_menu(message):
        user_id = message.from_user.id
        cfg = get_user_config(user_id)
        new_val = not cfg["highlight_medical"]
        update_user_config(user_id, {"highlight_medical": new_val})
        status_txt = "🟢 مفعل (أخضر زمردي)" if new_val else "⚪ معطل (نفس لون النص)"
        bot.send_message(
            message.chat.id,
            f"🩺 <b>تم تعديل تظليل المصطلحات الطبية:</b>\nالحالة الحالية: <b>{status_txt}</b>\n\n<i>تم الحفظ بنجاح!</i>"
        )

    @bot.message_handler(func=lambda msg: msg.text == "🔄 استعادة الافتراضي")
    def on_reset_defaults_menu(message):
        user_id = message.from_user.id
        save_user_setting(str(user_id), dict(DEFAULT_USER_CONFIG))
        bot.send_message(
            message.chat.id,
            "🔄 <b>تمت استعادة الإعدادات الافتراضية بنجاح!</b>\n"
            "• حجم الخط: 6.5 pt\n"
            "• اللون: 🔵 أزرق ملكي\n"
            "• تظليل المصطلحات: 🟢 مفعل\n\n"
            "<i>جاهز لترجمة ملفاتك.</i>"
        )

    # ---------------- Inline Query Callbacks ---------------- #
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
                reply_markup=build_settings_inline_keyboard(user_id)
            )
        except Exception:
            pass

    # ---------------- PDF Document Processing ---------------- #
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
        med_display = "🟢 مفعل (زمردي)" if cfg["highlight_medical"] else "⚪ معطل"

        # Structured Receipt Box
        receipt_box = (
            "┌──────────────────────────────┐\n"
            "│  📥 <b>تم استلام الملف بنجاح!</b>    │\n"
            "└──────────────────────────────┘\n"
            f"📄 <b>الملف:</b> <code>{doc.file_name}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>الإعدادات المعتمدة للترجمة:</b>\n"
            f"├ 📏 <b>حجم الخط:</b> <code>{sz_display}</code>\n"
            f"├ 🎨 <b>لون الترجمة:</b> <code>{cfg['color_label']}</code>\n"
            f"├ 🩺 <b>تظليل المصطلحات:</b> <code>{med_display}</code>\n"
            "└ 📐 <b>نمط المحاذاة:</b> <code>متوازن لليمين</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <b>جاري التحميل والمعالجة التفرعية الفائقة...</b>"
        )

        status_msg = bot.reply_to(message, receipt_box)

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
                if now - last_edit_time[0] > 2.5 or cur == total:
                    last_edit_time[0] = now
                    pct = int((cur / max(1, total)) * 100)
                    bar_len = 10
                    filled = int(bar_len * (cur / max(1, total)))
                    bar = "█" * filled + "░" * (bar_len - filled)
                    progress_box = (
                        "┌──────────────────────────────┐\n"
                        "│  ⚙️ <b>جاري الترجمة البينية...</b>    │\n"
                        "└──────────────────────────────┘\n"
                        f"📄 <b>الملف:</b> <code>{doc.file_name}</code>\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📊 <b>التقدم:</b> صفحة <code>{cur}</code> من <code>{total}</code>\n"
                        f"📈 <b>النسبة:</b> <code>[{bar}] {pct}%</code>\n"
                        f"💬 <b>الحالة:</b> <i>{text}</i>\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "⚡ <i>ترجمة تفرعية عبر 8 مسارات متزامنة...</i>"
                    )
                    try:
                        bot.edit_message_text(
                            progress_box,
                            chat_id,
                            status_msg.message_id
                        )
                    except Exception:
                        pass

            # 2. Run Translator with User Config
            color_tuple = tuple(float(c) for c in cfg["color_tuple"])
            font_sz = float(cfg["font_size"]) if cfg["font_size"] is not None else None

            translator = PDFInterlinearTranslator(
                input_pdf_path=input_pdf_path,
                output_pdf_path=output_pdf_path,
                font_size=font_sz,
                color=color_tuple,
                highlight_medical=cfg["highlight_medical"],
                progress_callback=progress_callback
            )

            t0 = time.time()
            result = translator.process()
            elapsed = time.time() - t0

            # 3. Send back the translated PDF with structured fields
            delivery_caption = (
                "┌──────────────────────────────┐\n"
                "│  🎉 <b>اكتملت الترجمة البينية!</b>   │\n"
                "└──────────────────────────────┘\n"
                f"📁 <b>الملف:</b> <code>Translated_{doc.file_name}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📊 <b>إحصائيات الإنجاز:</b>\n"
                f"├ 📄 <b>عدد الصفحات:</b> <code>{result.get('pages', 0)} صفحات</code>\n"
                f"├ 📝 <b>الأسطر المترجمة:</b> <code>{result.get('lines', 0)} سطر</code>\n"
                f"├ ⏱️ <b>سرعة المعالجة:</b> <code>{elapsed:.1f} ثانية ⚡</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚙️ <b>الإعدادات المعتمدة:</b>\n"
                f"├ 📏 <b>حجم الخط:</b> <code>{sz_display}</code>\n"
                f"├ 🎨 <b>لون الترجمة:</b> <code>{cfg['color_label']}</code>\n"
                f"└ 🩺 <b>المصطلحات الطبية:</b> <code>{med_display}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "💾 <i>إعداداتك محفوظة دائماً لأي ملف قادم!</i>"
            )

            with open(output_pdf_path, "rb") as out_file:
                bot.send_document(
                    chat_id,
                    out_file,
                    caption=delivery_caption,
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
    print(" Interlinear PDF Translator - Telegram Bot v2.0 ONLINE ")
    print(" Listening for incoming documents 24/7...")
    print("====================================================")
    bot.infinity_polling(timeout=20, long_polling_timeout=15)


if __name__ == "__main__":
    main()
