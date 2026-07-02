from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
QUESTION_PDF = ROOT / "2025r07a_ap_am_qs.pdf"
ANSWER_PDF = ROOT / "2025r07a_ap_am_ans.pdf"
ASSET_DIR = ROOT / "assets" / "questions"
DATA_FILE = ROOT / "questions.js"

SCALE = 2
FIRST_QUESTION_PAGE_INDEX = 3
LAST_QUESTION_PAGE_INDEX = 37


def parse_answers() -> dict[int, dict[str, str]]:
    with pdfplumber.open(ANSWER_PDF) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    answers: dict[int, dict[str, str]] = {}
    for number, answer, category in re.findall(r"問(\d+)\s+([アイウエ])\s+([ＴＭＳ])", text):
        answers[int(number)] = {"answer": answer, "category": category}
    if len(answers) != 80:
        raise RuntimeError(f"Expected 80 answers, found {len(answers)}")
    return answers


def render_pages() -> dict[int, Image.Image]:
    pdf = pdfium.PdfDocument(str(QUESTION_PDF))
    pages: dict[int, Image.Image] = {}
    for page_index in range(FIRST_QUESTION_PAGE_INDEX, LAST_QUESTION_PAGE_INDEX + 1):
        pages[page_index] = pdf[page_index].render(scale=SCALE).to_pil().convert("RGB")
    return pages


def find_question_starts(pages: dict[int, Image.Image]) -> list[tuple[int, int]]:
    template_page = pages[FIRST_QUESTION_PAGE_INDEX].convert("L")
    template = np.array(template_page.crop((104, 145, 131, 181))) < 160
    th, tw = template.shape
    template_count = int(template.sum())

    starts: list[tuple[int, int]] = []
    for page_index, image in pages.items():
        array = np.array(image.convert("L")) < 170
        hits: list[tuple[int, float]] = []
        for y in range(50, array.shape[0] - th - 120):
            best_score = -999.0
            for x in range(85, 122):
                window = array[y : y + th, x : x + tw]
                overlap = int((window & template).sum())
                extra = int((window & ~template).sum())
                missed = int((template & ~window).sum())
                score = (overlap - 0.25 * extra - 0.7 * missed) / template_count
                if score > best_score:
                    best_score = score
            if best_score > 0.38:
                hits.append((y, best_score))

        page_starts: list[tuple[int, float]] = []
        for hit in hits:
            if not page_starts or hit[0] - page_starts[-1][0] > 25:
                page_starts.append(hit)
            elif hit[1] > page_starts[-1][1]:
                page_starts[-1] = hit
        starts.extend((page_index, y) for y, _score in page_starts)

    if len(starts) != 80:
        counts = {}
        for page_index, _y in starts:
            counts[page_index + 1] = counts.get(page_index + 1, 0) + 1
        raise RuntimeError(f"Expected 80 question starts, found {len(starts)}: {counts}")
    return starts


def trim_crop(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    crop = image.crop(box)
    gray = np.array(crop.convert("L"))
    dark = gray < 210
    rows = np.where(dark.sum(axis=1) > 3)[0]
    cols = np.where(dark.sum(axis=0) > 3)[0]
    if len(rows) == 0 or len(cols) == 0:
        return crop
    top = max(int(rows[0]) - 24, 0)
    bottom = min(int(rows[-1]) + 36, crop.height)
    left = max(int(cols[0]) - 28, 0)
    right = min(int(cols[-1]) + 28, crop.width)
    return crop.crop((left, top, right, bottom))


def build_question_images(
    pages: dict[int, Image.Image],
    starts: list[tuple[int, int]],
    answers: dict[int, dict[str, str]],
) -> list[dict[str, object]]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in ASSET_DIR.glob("q*.png"):
        old_file.unlink()

    content_left = 70
    content_right = 960
    content_top = 90
    content_bottom = 1300
    items: list[dict[str, object]] = []

    for index, (page_index, start_y) in enumerate(starts, start=1):
        next_start = starts[index] if index < len(starts) else None
        segments: list[str] = []

        segment_pages = [page_index]
        if next_start is not None:
            segment_pages.extend(range(page_index + 1, next_start[0] + 1))

        for segment_no, segment_page in enumerate(segment_pages, start=1):
            image = pages[segment_page]
            top = max(start_y - 34, content_top) if segment_page == page_index else content_top
            if next_start is not None and segment_page == next_start[0]:
                bottom = max(next_start[1] - 28, top + 60)
            else:
                bottom = content_bottom
            if bottom <= top:
                continue

            cropped = trim_crop(image, (content_left, top, content_right, bottom))
            dark_pixels = int((np.array(cropped.convert("L")) < 210).sum())
            if cropped.height < 40 or cropped.width < 80 or dark_pixels < 2500:
                continue
            filename = f"q{index:02d}_{segment_no}.png"
            cropped.save(ASSET_DIR / filename, optimize=True)
            segments.append(f"assets/questions/{filename}")

        answer = answers[index]
        items.append(
            {
                "number": index,
                "answer": answer["answer"],
                "category": answer["category"],
                "images": segments,
            }
        )
    return items


def write_data(items: list[dict[str, object]]) -> None:
    payload = json.dumps(items, ensure_ascii=False, indent=2)
    DATA_FILE.write_text(f"window.QUESTIONS = {payload};\n", encoding="utf-8")


def main() -> None:
    answers = parse_answers()
    pages = render_pages()
    starts = find_question_starts(pages)
    items = build_question_images(pages, starts, answers)
    write_data(items)
    print(f"Generated {len(items)} questions in {ASSET_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
