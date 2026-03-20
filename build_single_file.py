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
P5_URL    = "https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"
P5SND_URL = "https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/addons/p5.sound.min.js"

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
    Replace the dynamic module-loader <script> block with a single inlined
    <script> containing all concatenated JS modules.

    The loader block starts with a line containing 'const _modules = [' and is
    wrapped in the nearest enclosing <script>…</script>.
    """
    # Greedily match the script block that contains the module loader sentinel
    pattern = re.compile(
        r'<script>\s*(?://[^\n]*\n\s*)?const _v\s*=.*?</script>',
        re.DOTALL,
    )
    replacement = f'<script id="app-js">\n{concatenated_js}\n</script>'
    result, n = pattern.subn(lambda _m: replacement, html, count=1)
    if n == 0:
        print("  WARNING: module-loader block not found in template. Appending JS before </body>.")
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

    # 2. Fetch / cache CDN libraries
    print("\nFetching CDN libraries …")
    p5_code  = fetch_and_cache(P5_URL,    ".cache/p5.min.js")
    snd_code = fetch_and_cache(P5SND_URL, ".cache/p5.sound.min.js")
    print(f"  p5.js       {len(p5_code):,} chars")
    print(f"  p5.sound.js {len(snd_code):,} chars")

    # 3. Concatenate JS modules
    print("\nConcatenating JS modules …")
    app_js = concatenate_modules(js_dir)
    print(f"  Total app JS: {len(app_js):,} chars")

    # 4. Inline p5.js and p5.sound.js
    print("\nInlining CDN scripts …")
    html = inline_cdn_tag(html, P5_URL,    p5_code)
    html = inline_cdn_tag(html, P5SND_URL, snd_code)

    # 5. Replace module loader with concatenated JS
    print("Inlining app JS …")
    html = inline_module_loader(html, app_js)

    # 6. Extract and insert embedded asset tags from old single-file
    assets_block = extract_embedded_assets(singlefile_path)
    if assets_block:
        # Insert immediately after <body>
        html = html.replace("<body>", f"<body>\n<!-- EMBEDDED ASSETS -->\n{assets_block}\n<!-- /EMBEDDED ASSETS -->", 1)
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
