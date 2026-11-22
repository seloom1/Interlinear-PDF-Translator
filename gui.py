"""
Interlinear PDF Translator - Modern PySide6 GUI (Precision Medical Edition)
- Direct Font Size Control: strictly applies user-selected font size
- Word-Level Medical Highlighting: highlights ONLY the exact medical term in green
- Balanced Right Alignment (centered with a gentle rightward bias)
- Pure Natural Arabic Typography (RTL from Right to Left, clean and coherent)
- Smart Sentence-Aware Context: merges connected lines for complete meaning
- Deep OCR & Image Scanning: never skips scanned pages, mixed pages, or diagrams
"""

import os
import sys
import subprocess
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QProgressBar, QComboBox,
    QCheckBox, QRadioButton, QButtonGroup, QLineEdit, QGroupBox,
    QMessageBox, QFrame, QColorDialog
)

import pymupdf
from translator_core import PDFInterlinearTranslator, get_default_arabic_font


class TranslationWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            translator = PDFInterlinearTranslator(
                input_pdf_path=self.params["input_path"],
                output_pdf_path=self.params["output_path"],
                font_size=self.params["font_size"],
                color=self.params["color"],
                vertical_offset=self.params["vertical_offset"],
                alignment=self.params.get("alignment", "balanced_right"),
                highlight_medical=self.params.get("highlight_medical", True),
                bg_highlight=self.params["bg_highlight"],
                page_range=self.params["page_range"],
                enable_ocr=self.params.get("enable_ocr", True),
                force_ocr=self.params.get("force_ocr", False),
                smart_context=self.params.get("smart_context", True),
                progress_callback=self._on_progress,
                cancel_check=lambda: self._is_cancelled
            )
            result = translator.process()
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(str(e))

    def _on_progress(self, current, total, text):
        self.progress.emit(current, total, text)


class DropZone(QFrame):
    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(95)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #3b82f6;
                border-radius: 12px;
                background-color: #f8fafc;
            }
            QFrame:hover {
                background-color: #eff6ff;
                border-color: #2563eb;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel("📄")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 24px; background: transparent; border: none;")

        self.text_label = QLabel("اسحب وأفلت ملف الـ PDF هنا، أو اضغط على الزر أدناه")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #475569; background: transparent; border: none;")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".pdf") for u in urls):
                event.acceptProposedAction()
                self.setStyleSheet("""
                    QFrame {
                        border: 2px dashed #10b981;
                        border-radius: 12px;
                        background-color: #ecfdf5;
                    }
                """)
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #3b82f6;
                border-radius: 12px;
                background-color: #f8fafc;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for u in urls:
            path = u.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.file_dropped.emit(path)
                break
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #3b82f6;
                border-radius: 12px;
                background-color: #f8fafc;
            }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مترجم الـ PDF البيني (التحكم الدقيق بحجم الخط وتمييز الكلمات الطبية)")
        self.resize(810, 800)
        self.setMinimumSize(720, 720)
        self.setLayoutDirection(Qt.RightToLeft)

        self.selected_file = None
        self.last_output_file = None
        self.worker = None
        self.custom_color = (0.08, 0.35, 0.78)

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(10)

        # Header Title
        title_label = QLabel("أداة ترجمة ملفات PDF بين السطور (التحكم الدقيق بالخط والمصطلحات)")
        title_label.setObjectName("headerTitle")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        sub_label = QLabel("تغيير حجم الخط بدقة كاملة | تظليل الكلمة الطبية فقط باللون الأخضر دون باقي الجملة | موضع متوازن مائل لليمين")
        sub_label.setObjectName("headerSub")
        sub_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(sub_label)

        # File Drop Zone
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        main_layout.addWidget(self.drop_zone)

        # File Chooser Row
        file_row = QHBoxLayout()
        self.btn_browse = QPushButton("📁 تصفح لاختيار ملف PDF...")
        self.btn_browse.setObjectName("btnBrowse")
        self.btn_browse.clicked.connect(self._browse_file)

        self.lbl_file_info = QLabel("لم يتم اختيار أي ملف بعد")
        self.lbl_file_info.setObjectName("fileInfo")
        file_row.addWidget(self.btn_browse)
        file_row.addWidget(self.lbl_file_info, stretch=1)
        main_layout.addLayout(file_row)

        # Features Card
        features_group = QGroupBox("إعدادات الخط والمحاذاة والمصطلحات الطبية")
        features_layout = QVBoxLayout(features_group)
        features_layout.setSpacing(8)

        # Row 1: Font size selection & Alignment
        row1 = QHBoxLayout()
        lbl_size = QLabel("حجم خط الترجمة:")
        self.combo_size = QComboBox()
        self.combo_size.addItems([
            "تلقائي متناسق (~56% من السطر الأصلي)",
            "4.5 نقطة (صغير جداً ومدمج)",
            "5.5 نقطة (صغير متناسق)",
            "6.5 نقطة (متوسط - واضح)",
            "7.5 نقطة (واضح ومميز - كبير)",
            "8.5 نقطة (كبير جداً)",
            "9.5 نقطة (بارز ضخم)",
            "11.0 نقطة (عملاق)"
        ])
        # Default index: 0 (Auto) or user chooses freely

        lbl_align = QLabel("موضع المحاذاة:")
        self.combo_align = QComboBox()
        self.combo_align.addItems([
            "متوسط السطر مائل لليمين قليلاً (موصى به)",
            "توسيط كامل فوق السطر",
            "محاذاة كاملة لليمين",
            "محاذاة لليسار"
        ])

        row1.addWidget(lbl_size)
        row1.addWidget(self.combo_size, stretch=1)
        row1.addSpacing(16)
        row1.addWidget(lbl_align)
        row1.addWidget(self.combo_align, stretch=1)
        features_layout.addLayout(row1)

        # Row 2: Medical word-level checkbox
        self.chk_medical = QCheckBox("🟢 تمييز الكلمة الطبية فقط باللون الأخضر (Word-Level Medical Badge - دون تلوين باقي الجملة)")
        self.chk_medical.setChecked(True)
        self.chk_medical.setStyleSheet("font-weight: 700; color: #047857;")
        features_layout.addWidget(self.chk_medical)

        # Row 3: Smart context
        self.chk_smart_context = QCheckBox("ترجمة ذكية للسياق (دمج الأسطر المتصلة التي لا تنتهي بنقطة لاكتمال المعنى)")
        self.chk_smart_context.setChecked(True)
        self.chk_smart_context.setStyleSheet("font-weight: 600; color: #1e3a8a;")
        features_layout.addWidget(self.chk_smart_context)

        # Row 4: OCR Options
        ocr_row = QHBoxLayout()
        self.chk_ocr = QCheckBox("فحص شامل للصور والمستندات الممسوحة (OCR تلقائي لعدم تخطي أي صفحة أو صورة)")
        self.chk_ocr.setChecked(True)
        self.chk_force_ocr = QCheckBox("إجبار OCR على كل الصفحات")
        self.chk_force_ocr.setChecked(False)
        ocr_row.addWidget(self.chk_ocr, stretch=2)
        ocr_row.addWidget(self.chk_force_ocr, stretch=1)
        features_layout.addLayout(ocr_row)

        main_layout.addWidget(features_group)

        # Appearance Card
        options_group = QGroupBox("المظهر والألوان")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(10)

        # Row: Color, Offset, Background
        row_app = QHBoxLayout()
        lbl_color = QLabel("لون الكلمات العادية:")
        self.combo_color = QComboBox()
        self.combo_color.addItems([
            "أزرق ملكي أنيق (موصى به)",
            "أحمر عنابي واضح",
            "رمادي داكن متناسق",
            "أخضر زمردي",
            "أسود خالص",
            "تخصيص لون آخر..."
        ])
        self.combo_color.currentIndexChanged.connect(self._on_color_changed)

        lbl_offset = QLabel("المسافة فوق السطر:")
        self.combo_offset = QComboBox()
        self.combo_offset.addItems([
            "ملاصق جداً (0.5 pt)",
            "متناسق وقريب (0.8 pt) - موصى به",
            "متوسط (1.2 pt)",
            "متباعد قليلاً (1.8 pt)"
        ])
        self.combo_offset.setCurrentIndex(1)

        self.chk_bg = QCheckBox("شريط حماية خلفي رقيق يمنع تداخل الحروف")
        self.chk_bg.setChecked(True)

        row_app.addWidget(lbl_color)
        row_app.addWidget(self.combo_color, stretch=1)
        row_app.addSpacing(12)
        row_app.addWidget(lbl_offset)
        row_app.addWidget(self.combo_offset)
        row_app.addSpacing(12)
        row_app.addWidget(self.chk_bg, stretch=1)
        options_layout.addLayout(row_app)

        # Row: Page Range
        row_page = QHBoxLayout()
        lbl_pages = QLabel("نطاق الصفحات:")
        self.radio_all = QRadioButton("كل الصفحات")
        self.radio_all.setChecked(True)
        self.radio_custom = QRadioButton("صفحات محددة:")
        self.txt_pages = QLineEdit()
        self.txt_pages.setPlaceholderText("مثال: 1-5, 8, 12")
        self.txt_pages.setEnabled(False)
        self.radio_custom.toggled.connect(lambda checked: self.txt_pages.setEnabled(checked))

        page_group = QButtonGroup(self)
        page_group.addButton(self.radio_all)
        page_group.addButton(self.radio_custom)

        row_page.addWidget(lbl_pages)
        row_page.addWidget(self.radio_all)
        row_page.addWidget(self.radio_custom)
        row_page.addWidget(self.txt_pages, stretch=1)
        options_layout.addLayout(row_page)

        main_layout.addWidget(options_group)

        # Progress Section
        progress_group = QGroupBox("حالة المعالجة والتقدم")
        progress_layout = QVBoxLayout(progress_group)
        self.prog_bar = QProgressBar()
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(True)
        self.lbl_status = QLabel("جاهز للبدء.")
        self.lbl_status.setStyleSheet("color: #475569; font-weight: 500;")

        progress_layout.addWidget(self.prog_bar)
        progress_layout.addWidget(self.lbl_status)
        main_layout.addWidget(progress_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("🚀 بدء الترجمة الفورية")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self._start_translation)

        self.btn_cancel = QPushButton("إلغاء")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_translation)

        self.btn_open_file = QPushButton("📖 فتح الملف المترجم")
        self.btn_open_file.setObjectName("btnSuccess")
        self.btn_open_file.setEnabled(False)
        self.btn_open_file.clicked.connect(self._open_output_file)

        self.btn_open_folder = QPushButton("📂 فتح مجلد الحفظ")
        self.btn_open_folder.setObjectName("btnSecondary")
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.clicked.connect(self._open_output_folder)

        btn_layout.addWidget(self.btn_start, stretch=2)
        btn_layout.addWidget(self.btn_cancel, stretch=1)
        btn_layout.addWidget(self.btn_open_file, stretch=1)
        btn_layout.addWidget(self.btn_open_folder, stretch=1)
        main_layout.addLayout(btn_layout)

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                background-color: #f1f5f9;
                color: #1e293b;
            }
            #headerTitle {
                font-size: 19px;
                font-weight: 700;
                color: #0f172a;
            }
            #headerSub {
                font-size: 12px;
                color: #64748b;
                margin-bottom: 2px;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                margin-top: 6px;
                padding: 10px;
                font-weight: 600;
                color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                right: 14px;
                padding: 0 6px;
            }
            #btnBrowse {
                background-color: #ffffff;
                border: 1px solid #94a3b8;
                padding: 7px 14px;
                border-radius: 6px;
                font-weight: 600;
            }
            #btnBrowse:hover {
                background-color: #e2e8f0;
            }
            #fileInfo {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 7px 12px;
                color: #334155;
            }
            QComboBox, QLineEdit {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 5px 8px;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #3b82f6;
            }
            QProgressBar {
                background-color: #e2e8f0;
                border-radius: 6px;
                text-align: center;
                height: 22px;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 6px;
            }
            #btnStart {
                background-color: #2563eb;
                color: white;
                font-weight: 700;
                font-size: 14px;
                border-radius: 8px;
                padding: 10px 16px;
                border: none;
            }
            #btnStart:hover {
                background-color: #1d4ed8;
            }
            #btnStart:disabled {
                background-color: #94a3b8;
            }
            #btnCancel {
                background-color: #ef4444;
                color: white;
                font-weight: 600;
                border-radius: 8px;
                padding: 10px 16px;
                border: none;
            }
            #btnCancel:hover {
                background-color: #dc2626;
            }
            #btnCancel:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
            #btnSuccess {
                background-color: #10b981;
                color: white;
                font-weight: 600;
                border-radius: 8px;
                padding: 10px 14px;
                border: none;
            }
            #btnSuccess:hover {
                background-color: #059669;
            }
            #btnSuccess:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
            #btnSecondary {
                background-color: #64748b;
                color: white;
                font-weight: 600;
                border-radius: 8px;
                padding: 10px 14px;
                border: none;
            }
            #btnSecondary:hover {
                background-color: #475569;
            }
            #btnSecondary:disabled {
                background-color: #cbd5e1;
                color: #94a3b8;
            }
        """)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف PDF للترجمة",
            "",
            "ملفات PDF (*.pdf);;جميع الملفات (*.*)"
        )
        if file_path:
            self._on_file_selected(file_path)

    def _on_file_selected(self, path):
        self.selected_file = path
        try:
            doc = pymupdf.open(path)
            num_pages = len(doc)
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            doc.close()
            self.lbl_file_info.setText(
                f"📄 {os.path.basename(path)} ({num_pages} صفحة | {file_size_mb:.2f} MB)"
            )
            self.lbl_status.setText("تم تحميل الملف بنجاح. اضغط 'بدء الترجمة' للمتابعة.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في قراءة الملف", f"تعذر فتح ملف الـ PDF:\n{str(e)}")

    def _on_color_changed(self, idx):
        if idx == 0:
            self.custom_color = (0.08, 0.35, 0.78)
        elif idx == 1:
            self.custom_color = (0.75, 0.12, 0.12)
        elif idx == 2:
            self.custom_color = (0.22, 0.28, 0.35)
        elif idx == 3:
            self.custom_color = (0.08, 0.55, 0.25)
        elif idx == 4:
            self.custom_color = (0.0, 0.0, 0.0)
        elif idx == 5:
            col = QColorDialog.getColor(QColor(20, 89, 198), self, "اختر لون الترجمة")
            if col.isValid():
                self.custom_color = (col.redF(), col.greenF(), col.blueF())

    def _parse_page_range(self, text, total_pages):
        pages = set()
        parts = text.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                s, e = part.split("-", 1)
                s = int(s.strip()) - 1
                e = int(e.strip()) - 1
                for p in range(max(0, s), min(total_pages, e + 1)):
                    pages.add(p)
            else:
                p = int(part) - 1
                if 0 <= p < total_pages:
                    pages.add(p)
        return sorted(list(pages))

    def _start_translation(self):
        if not self.selected_file:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار ملف PDF أولاً.")
            return

        size_idx = self.combo_size.currentIndex()
        size_values = [None, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 11.0]
        font_size = size_values[size_idx]

        offset_map = [0.5, 0.8, 1.2, 1.8]
        v_offset = offset_map[self.combo_offset.currentIndex()]
        bg_highlight = self.chk_bg.isChecked()
        enable_ocr = self.chk_ocr.isChecked()
        force_ocr = self.chk_force_ocr.isChecked()
        smart_context = self.chk_smart_context.isChecked()
        highlight_medical = self.chk_medical.isChecked()

        # Alignment
        align_idx = self.combo_align.currentIndex()
        align_map = ["balanced_right", "center", "right", "left"]
        alignment = align_map[align_idx]

        page_range = None
        if self.radio_custom.isChecked():
            try:
                doc = pymupdf.open(self.selected_file)
                total_p = len(doc)
                doc.close()
                page_range = self._parse_page_range(self.txt_pages.text(), total_p)
                if not page_range:
                    QMessageBox.warning(self, "تنبيه", "نطاق الصفحات المحدد غير صالح أو فارغ.")
                    return
            except Exception as e:
                QMessageBox.warning(self, "تنبيه", f"خطأ في قراءة نطاق الصفحات:\n{str(e)}")
                return

        self.btn_start.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_open_file.setEnabled(False)
        self.btn_open_folder.setEnabled(False)
        self.prog_bar.setValue(0)
        self.lbl_status.setText("جاري تهيئة المعالجة وفحص الصفحات...")

        params = {
            "input_path": self.selected_file,
            "output_path": None,
            "font_size": font_size,
            "color": self.custom_color,
            "vertical_offset": v_offset,
            "alignment": alignment,
            "highlight_medical": highlight_medical,
            "bg_highlight": bg_highlight,
            "page_range": page_range,
            "enable_ocr": enable_ocr,
            "force_ocr": force_ocr,
            "smart_context": smart_context
        }

        self.worker = TranslationWorker(params)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    def _cancel_translation(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.lbl_status.setText("جاري الإلغاء...")
            self.btn_cancel.setEnabled(False)

    def _on_worker_progress(self, current, total, text):
        percent = int((current / max(1, total)) * 100)
        self.prog_bar.setValue(percent)
        self.lbl_status.setText(text)

    def _on_worker_finished(self, result):
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if result.get("status") == "cancelled":
            self.lbl_status.setText("تم إلغاء عملية الترجمة.")
            self.prog_bar.setValue(0)
            return

        self.last_output_file = result.get("output_path")
        self.btn_open_file.setEnabled(True)
        self.btn_open_folder.setEnabled(True)
        self.prog_bar.setValue(100)

        lines_cnt = result.get("lines", 0)
        pages_cnt = result.get("pages", 0)
        self.lbl_status.setText(f"🎉 اكتمل بنجاح! تم ترجمة {lines_cnt} سطر عبر {pages_cnt} صفحة.")
        QMessageBox.information(
            self,
            "اكتملت الترجمة",
            f"تمت معالجة وترجمة الملف بنجاح!\n\n"
            f"• عدد الأسطر المترجمة: {lines_cnt}\n"
            f"• الملف الناتج:\n{self.last_output_file}"
        )

    def _on_worker_failed(self, error_str):
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText("حدث خطأ أثناء الترجمة.")
        QMessageBox.critical(self, "خطأ", f"تعذر إكمال عملية الترجمة:\n{error_str}")

    def _open_output_file(self):
        if self.last_output_file and os.path.exists(self.last_output_file):
            try:
                os.startfile(self.last_output_file)
            except Exception:
                subprocess.Popen(["start", "", self.last_output_file], shell=True)

    def _open_output_folder(self):
        if self.last_output_file:
            folder = os.path.dirname(os.path.abspath(self.last_output_file))
            try:
                os.startfile(folder)
            except Exception:
                subprocess.Popen(["explorer", folder])


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
