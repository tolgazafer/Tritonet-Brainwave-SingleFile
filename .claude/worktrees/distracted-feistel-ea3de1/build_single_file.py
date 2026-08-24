#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import re
import urllib.request


P5_CDN_URL = "https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"
P5_SCRIPT_TAG_PATTERN = re.compile(
    r"<script\s+src=\"https://cdnjs\.cloudflare\.com/ajax/libs/p5\.js/1\.9\.0/p5\.min\.js\"></script>"
)

def fetch_p5_code(cache_file: pathlib.Path) -> str:
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    with urllib.request.urlopen(P5_CDN_URL, timeout=30) as response:
        content = response.read().decode("utf-8")

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(content, encoding="utf-8")
    return content


def inline_p5(single_file_path: pathlib.Path, p5_code: str) -> bool:
    html = single_file_path.read_text(encoding="utf-8")
    replacement = f"<script>\n{p5_code}\n</script>"
    updated, count = P5_SCRIPT_TAG_PATTERN.subn(lambda _m: replacement, html, count=1)
    if count == 0:
        return False
    single_file_path.write_text(updated, encoding="utf-8")
    return True


APP_SCRIPT_TAG = '<script id="app-js">'


def replace_embedded_app_js(single_file_path: pathlib.Path, app_js_path: pathlib.Path) -> bool:
    html = single_file_path.read_text(encoding="utf-8")
    script_start = html.find(APP_SCRIPT_TAG)
    if script_start == -1:
        return False

    script_end = html.find("</script>", script_start)
    if script_end == -1:
        return False

    app_js = app_js_path.read_text(encoding="utf-8").rstrip()
    replacement = f'{APP_SCRIPT_TAG}\n{app_js}\n</script>'
    updated = html[:script_start] + replacement + html[script_end + len("</script>"):]
    single_file_path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inline p5.js into Tritonet single-file HTML")
    parser.add_argument(
        "--single-file",
        default="Tritonet_Brainwave_SingleFile.html",
        help="Path to single-file HTML",
    )
    parser.add_argument(
        "--cache-file",
        default=".cache/p5.min.js",
        help="Local cache path for p5.min.js",
    )
    parser.add_argument(
        "--app-js",
        default="JavaScript/Tritonet_Brainwave.js",
        help="Path to source app JavaScript file to embed",
    )
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parent
    single_file_path = (root / args.single_file).resolve()
    cache_file = (root / args.cache_file).resolve()
    app_js_path = (root / args.app_js).resolve()

    p5_code = fetch_p5_code(cache_file)
    p5_replaced = inline_p5(single_file_path, p5_code)
    js_replaced = replace_embedded_app_js(single_file_path, app_js_path)

    if p5_replaced:
        print(f"Inlined p5.js in: {single_file_path}")
    else:
        print("No external p5.js CDN tag found; file may already be inlined.")

    if js_replaced:
        print(f"Embedded latest app JS from: {app_js_path}")
    else:
        print("Could not find embedded app JS marker in single-file HTML.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
