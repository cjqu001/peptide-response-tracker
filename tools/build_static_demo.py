# build_static_demo.py - Builds docs/index.html, a static GitHub Pages demo of the tracker.
# It copies templates/index.html, injects tools/demo_mock_api.js (an in-memory fake API
# seeded with the Example data), adds a demo banner, and routes CSV export to the browser.
# Run from the repo root:  python tools/build_static_demo.py
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
mock = (ROOT / "tools" / "demo_mock_api.js").read_text(encoding="utf-8")

BANNER = (
    '<div style="background:#fff4d6;color:#4a3b00;border-bottom:1px solid #e0c97a;'
    'padding:8px 16px;font-size:.9rem;text-align:center">'
    "<b>Live demo.</b> Sample data only. Nothing is saved; changes reset when you reload. "
    '<a href="https://github.com/cjqu001/peptide-response-tracker" style="color:inherit">'
    "Get the self-hosted app on GitHub</a></div>"
)
AFTER = "<script>window.exportCsv = () => demoExportCsv(profile);</script>"

assert html.count("<script>") == 1 and "<body" in html, "Template layout changed; update this script."
body_tag_end = html.index(">", html.index("<body")) + 1
html = html[:body_tag_end] + "\n" + BANNER + html[body_tag_end:]
html = html.replace("<script>", "<script>\n" + mock + "\n</script>\n<script>", 1)
html = html.replace("</body>", AFTER + "\n</body>", 1)
html = html.replace("<title>Habit Tracker", "<title>Peptide Response Tracker (demo)", 1)

out = ROOT / "docs" / "index.html"
out.write_text(html, encoding="utf-8")
print(f"Wrote {out}")
