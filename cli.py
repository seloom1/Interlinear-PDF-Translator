"""
Command Line Interface (CLI) for Interlinear PDF Translator (Word-Level Medical Edition).
"""

import sys
import os
import argparse
from translator_core import PDFInterlinearTranslator


def parse_color(color_str):
    color_map = {
        "blue": (0.08, 0.35, 0.78),
        "red": (0.75, 0.12, 0.12),
        "slate": (0.22, 0.28, 0.35),
        "green": (0.08, 0.55, 0.25),
        "black": (0.0, 0.0, 0.0)
    }
    low = color_str.lower().strip()
    if low in color_map:
        return color_map[low]
    if low.startswith("#") and len(low) == 7:
        r = int(low[1:3], 16) / 255.0
        g = int(low[3:5], 16) / 255.0
        b = int(low[5:7], 16) / 255.0
        return (r, g, b)
    return (0.08, 0.35, 0.78)


def parse_pages(pages_str, total_pages):
    if not pages_str:
        return None
    pages = set()
    for part in pages_str.split(","):
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


def main():
    parser = argparse.ArgumentParser(
        description="Interlinear PDF Translator (Word-Level Medical Highlighting & Precision Font Control)"
    )
    parser.add_argument("input_pdf", help="Path to input PDF file")
    parser.add_argument("-o", "--output", help="Path to output PDF file", default=None)
    parser.add_argument("-s", "--size", type=float, help="Font size in pt (e.g. 5.5, 6.5, 7.5, 8.5)", default=None)
    parser.add_argument("-c", "--color", help="Color: blue, red, slate, green, black, or #HEX", default="blue")
    parser.add_argument("--offset", type=float, help="Vertical offset in pt above caps (default: 0.8)", default=0.8)
    parser.add_argument(
        "--align",
        choices=["balanced_right", "center", "right", "left"],
        default="balanced_right",
        help="Horizontal alignment above line (default: balanced_right)"
    )
    parser.add_argument("--no-medical", action="store_true", help="Disable word-level green highlighting for medical terms")
    parser.add_argument("--no-bg", action="store_true", help="Disable white background pill behind Arabic text")
    parser.add_argument("-p", "--pages", help="Page range, e.g. 1-5, 8, 12", default=None)
    parser.add_argument("--no-ocr", action="store_true", help="Disable automatic OCR for scanned pages")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR on all pages")
    parser.add_argument("--no-smart-context", action="store_true", help="Disable smart sentence grouping across lines")

    args = parser.parse_args()

    if not os.path.exists(args.input_pdf):
        print(f"Error: File '{args.input_pdf}' not found.")
        sys.exit(1)

    import pymupdf
    doc = pymupdf.open(args.input_pdf)
    total_pages = len(doc)
    doc.close()

    page_range = parse_pages(args.pages, total_pages)
    color_tuple = parse_color(args.color)

    print(f"Starting translation: '{args.input_pdf}' ({total_pages} pages, font_size: {args.size or 'auto'}, medical: {not args.no_medical})")

    def progress(curr, total, status_text):
        print(f"[{curr}/{total}] {status_text}")

    translator = PDFInterlinearTranslator(
        input_pdf_path=args.input_pdf,
        output_pdf_path=args.output,
        font_size=args.size,
        color=color_tuple,
        vertical_offset=args.offset,
        alignment=args.align,
        highlight_medical=not args.no_medical,
        bg_highlight=not args.no_bg,
        page_range=page_range,
        enable_ocr=not args.no_ocr,
        force_ocr=args.force_ocr,
        smart_context=not args.no_smart_context,
        progress_callback=progress
    )

    stats = translator.process()
    print("Done!")
    print(f"Output saved: {stats['output_path']}")
    print(f"Total lines translated: {stats['lines']}")


if __name__ == "__main__":
    main()
