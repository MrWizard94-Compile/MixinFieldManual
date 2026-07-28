from pathlib import Path

build = Path(r"C:\WPAI\Software\MixinFieldManual\build")
html = (build / "MixinFieldManual.html").read_text(encoding="utf-8")
sample = (build / "MixinFieldManual-Sample.html").read_text(encoding="utf-8")

checks = {
    "fenced code rendered as <pre><code>": "<pre><code>" in html,
    "tables rendered as <table>/<th>": "<table>" in html and "<th>" in html,
    "no raw ``` fences leaked": "```" not in html,
    "no raw markdown table rules leaked": "|----" not in html and "| ---" not in html,
    "verified exception message present": "cannot inject into" in html,
    "neoforge correction present": "dropped SRG as the runtime intermediary" in html,
    "13 chapter sections": html.count('<section class="chapter">') == 13,
    "TOC has all 12 numbered chapters": all(f"{n}. " in html for n in range(1, 13)),
    "title page present": "The Mixin<br>Field Manual" in html,
    "sample: chapter 1 present": "The Collision" in sample,
    "sample: upsell outro present": "GUMROAD LINK" in sample,
    "sample: no other chapters leaked": "Wrapping the Wrapper" not in sample.replace(
        "wrapper", ""),  # ch5 title absent
}

failed = 0
for name, ok in checks.items():
    print(("PASS  " if ok else "FAIL  ") + name)
    failed += 0 if ok else 1

print(f"\n{len(checks) - failed}/{len(checks)} checks passed")
raise SystemExit(1 if failed else 0)
