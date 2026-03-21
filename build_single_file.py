#!/usr/bin/env python3
"""
Tritonet build script — assembles Tritonet_Web.html from multiple source files.

What it does:
  1. Reads JavaScript/index.html as the HTML template.
  2. Inlines p5.js and p5.sound.js (cached locally in .cache/).
  3. Concatenates all JS modules (JavaScript/js/*.js) in declared load order.
  4. Replaces the CDN script tags and module-loader block in the HTML with the
     inlined content so the result is a single, self-contained HTML file.
  5. Copies embedded asset <img> hidden tags from the existing single-file build
     (Tritonet_Brainwave_SingleFile.html) if present, so images/fonts still work.
  6. Writes the result to Tritonet_Web.html.
"""
from __future__ import annotations

import pathlib
import re
import urllib.request

# ---------------------------------------------------------------------------
# CDN URLs
# ---------------------------------------------------------------------------
P5_URL = "https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"
# p5.sound is NOT used — app uses Web Audio API directly.

# ---------------------------------------------------------------------------
# JS module load order  (must match index.html)
# ---------------------------------------------------------------------------
JS_MODULES = [
    "js/config.js",
    "js/colors.js",
    "js/themes.js",
    "js/mpe.js",
    "js/sequencer.js",
    "js/state.js",
    "js/audio-midi.js",
    "js/core.js",
    "js/drawing.js",
    "js/gui-input.js",
]

ROOT = pathlib.Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_and_cache(url: str, cache_rel: str) -> str:
    cache_path = (ROOT / cache_rel).resolve()
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")
    print(f"  Downloading {url} …")
    with urllib.request.urlopen(url, timeout=30) as r:
        content = r.read().decode("utf-8")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(content, encoding="utf-8")
    return content


def concatenate_modules(js_dir: pathlib.Path) -> str:
    parts: list[str] = []
    for rel in JS_MODULES:
        path = js_dir / rel
        if not path.exists():
            print(f"  WARNING: module not found: {path}")
            continue
        src = path.read_text(encoding="utf-8").rstrip()
        parts.append(f"// ===== MODULE: {rel} =====\n{src}")
        print(f"  + {rel}  ({len(src):,} chars)")
    return "\n\n".join(parts)


def extract_embedded_fonts(singlefile_path: pathlib.Path) -> str:
    """Extract @font-face declarations from the old single-file HTML's <style> block."""
    if not singlefile_path.exists():
        return ""
    html = singlefile_path.read_text(encoding="utf-8")
    font_re = re.compile(
        r'(@font-face\s*\{[^}]*font-family:\s*[\'"](?:Metdemo|Tritonet)Embedded[\'"][^}]*\})',
        re.DOTALL | re.IGNORECASE,
    )
    fonts = font_re.findall(html)
    if fonts:
        return "\n".join(fonts)
    return ""


def extract_embedded_assets(singlefile_path: pathlib.Path) -> str:
    """
    Pull the hidden <img> asset block out of the old single-file HTML so that
    the embedded images/fonts are available at runtime.
    Looks for <!-- EMBEDDED ASSETS --> … <!-- /EMBEDDED ASSETS --> markers,
    or falls back to collecting all <img id="_img_*"> tags.
    """
    if not singlefile_path.exists():
        return ""

    html = singlefile_path.read_text(encoding="utf-8")

    # Preferred: explicit marker block
    marker_re = re.compile(
        r'<!--\s*EMBEDDED ASSETS\s*-->(.*?)<!--\s*/EMBEDDED ASSETS\s*-->',
        re.DOTALL | re.IGNORECASE,
    )
    m = marker_re.search(html)
    if m:
        return m.group(0)

    # Fallback: collect individual hidden image tags
    img_re = re.compile(r'<img\s[^>]*id=["\']_img_[^>]*>', re.IGNORECASE)
    imgs = img_re.findall(html)
    if imgs:
        return "\n".join(imgs)

    return ""


def inline_cdn_tag(html: str, cdn_url: str, js_code: str) -> str:
    """Replace a <script src="cdn_url"></script> tag with an inlined block."""
    escaped_url = re.escape(cdn_url)
    pattern = re.compile(
        rf'<script\s+src="{escaped_url}(?:[^"]*)"[^>]*>\s*</script>',
        re.IGNORECASE,
    )
    replacement = f"<script>\n{js_code}\n</script>"
    result, n = pattern.subn(lambda _m: replacement, html, count=1)
    if n == 0:
        print(f"  WARNING: CDN tag not found in template for: {cdn_url}")
    return result


def inline_module_loader(html: str, concatenated_js: str) -> str:
    """
    Replace the <!-- BUILD:JS-START --> … <!-- BUILD:JS-END --> block
    (which contains the static <script src="js/..."> tags) with a single
    inlined <script id="app-js"> containing all concatenated JS modules.
    """
    pattern = re.compile(
        r'<!--\s*BUILD:JS-START\s*-->.*?<!--\s*BUILD:JS-END\s*-->',
        re.DOTALL,
    )
    replacement = f'<script id="app-js">\n{concatenated_js}\n</script>'
    result, n = pattern.subn(lambda _m: replacement, html, count=1)
    if n == 0:
        print("  WARNING: BUILD:JS-START marker not found. Appending JS before </body>.")
        result = html.replace(
            "</body>",
            f'<script id="app-js">\n{concatenated_js}\n</script>\n</body>',
            1,
        )
    return result


def remove_stub_scripts(html: str) -> str:
    """Remove the inline stub scripts (teacherSend, toggleMuteVoice, etc.)
    that are only needed during development to avoid JS errors."""
    # These are the two small inline <script> blocks after the module loader.
    # We leave them in — they are harmless stubs that get overridden at runtime.
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    js_dir        = ROOT / "JavaScript"
    template_path = js_dir / "index.html"
    output_path   = ROOT / "Tritonet_Web.html"
    singlefile_path = ROOT / "Tritonet_Brainwave_SingleFile.html"

    print("Tritonet build script")
    print("======================")

    # 1. Read template
    if not template_path.exists():
        print(f"ERROR: template not found: {template_path}")
        return 1
    html = template_path.read_text(encoding="utf-8")
    print(f"Template: {template_path}  ({len(html):,} chars)")

    # 2. Fetch / cache p5.js (p5.sound is NOT used — app uses Web Audio API)
    print("\nFetching CDN libraries …")
    p5_code  = fetch_and_cache(P5_URL, ".cache/p5.min.js")
    print(f"  p5.js  {len(p5_code):,} chars")

    # 3. Concatenate JS modules
    print("\nConcatenating JS modules …")
    app_js = concatenate_modules(js_dir)
    print(f"  Total app JS: {len(app_js):,} chars")

    # 4. Inline p5.js only
    print("\nInlining CDN scripts …")
    html = inline_cdn_tag(html, P5_URL, p5_code)
    # Remove the p5.sound comment line (not a real script tag, just a comment)
    html = html.replace(
        "  <!-- p5.sound is NOT used — the app uses Web Audio API directly -->", ""
    )

    # 5. Replace module loader with concatenated JS
    print("Inlining app JS …")
    html = inline_module_loader(html, app_js)

    # 6a. Extract and inject embedded @font-face CSS from old single-file
    font_css = extract_embedded_fonts(singlefile_path)
    if font_css:
        html = html.replace("</style>", f"\n    /* === EMBEDDED FONTS === */\n    {font_css}\n  </style>", 1)
        print(f"  Embedded fonts CSS: {len(font_css):,} chars")
    else:
        print("  No embedded fonts found.")

    # 6b. Extract and insert embedded asset <img> tags from old single-file
    assets_block = extract_embedded_assets(singlefile_path)
    if assets_block:
        html = html.replace("</head>\n<body>", f"</head>\n<body>\n<!-- EMBEDDED ASSETS -->\n{assets_block}\n<!-- /EMBEDDED ASSETS -->", 1)
        print(f"  Embedded assets block: {len(assets_block):,} chars")
    else:
        print("  No embedded assets found (images will load from file paths).")

    # 7. Write output
    output_path.write_text(html, encoding="utf-8")
    print(f"\nOutput: {output_path}  ({len(html):,} chars)")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
