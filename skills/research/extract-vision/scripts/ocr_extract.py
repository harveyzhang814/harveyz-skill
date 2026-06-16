#!/usr/bin/env python3
"""
PaddleOCR v3 文字提取脚本。
用法：python ocr_extract.py <image_path> [--lang en|ch|ch+en|fr|de|ja|ko]
输出：每行一条识别结果，格式为 `{text} | conf={score:.2f}`
"""
import argparse
import sys

MAX_PX = 4000
RESIZE_TO = 2000


def check_deps():
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        print("错误：未安装 paddleocr。请运行：pip install paddleocr", file=sys.stderr)
        sys.exit(1)


def maybe_resize(image_path: str) -> str:
    try:
        from PIL import Image
    except ImportError:
        return image_path

    img = Image.open(image_path)
    w, h = img.size
    if max(w, h) <= MAX_PX:
        return image_path

    if w >= h:
        new_w, new_h = RESIZE_TO, int(RESIZE_TO * h / w)
    else:
        new_w, new_h = int(RESIZE_TO * w / h), RESIZE_TO

    resized_path = image_path + ".resized.png"
    img.resize((new_w, new_h)).save(resized_path)
    print(f"[resize] {w}x{h} → {new_w}x{new_h}，已保存至 {resized_path}", file=sys.stderr)
    return resized_path


def run_ocr(image_path: str, lang: str) -> str:
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(lang=lang)
    result = ocr.ocr(image_path)

    if not result:
        return ""

    page = result[0]
    rec_texts = page.get("rec_texts", [])
    rec_scores = page.get("rec_scores", [])

    lines = [
        f"{text} | conf={score:.2f}"
        for text, score in zip(rec_texts, rec_scores)
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="从图像中提取全部文字（PaddleOCR v3）")
    parser.add_argument("image_path", help="图像文件路径")
    parser.add_argument("--lang", default="en",
                        choices=["en", "ch", "ch+en", "fr", "de", "ja", "ko"],
                        help="识别语言（默认：en）")
    args = parser.parse_args()

    check_deps()
    path = maybe_resize(args.image_path)
    text = run_ocr(path, args.lang)

    if not text:
        print("警告：OCR 未识别出任何文字。", file=sys.stderr)
        sys.exit(2)

    print(text)


if __name__ == "__main__":
    main()
