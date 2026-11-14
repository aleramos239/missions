"""Copy Homebase's look into missions/static/hb from Homebase `main` (git show only: never the working tree)."""
import subprocess
from pathlib import Path

HB = Path("~/ramos-quant-homebase").expanduser()
OUT = Path(__file__).resolve().parent.parent / "missions/static/hb"
FILES = {"shadcn": "homebase/static/shadcn.css", "symbols": "homebase/static/apple/symbols.css",
         "system": "homebase/static/apple/system.css", "desk": "homebase/static/apple/desk.css"}


def show(path):
    return subprocess.run(["git", "-C", str(HB), "show", f"main:{path}"], check=True, capture_output=True, text=True).stdout


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, path in FILES.items():
        (OUT / f"{name}.css").write_text(show(path))
    html = show("homebase/static/index.html")
    a = html.index("<style>") + len("<style>")
    (OUT / "chrome.css").write_text(html[a:html.index("</style>", a)])
    rev = subprocess.run(["git", "-C", str(HB), "rev-parse", "main"], check=True, capture_output=True, text=True).stdout
    (OUT / "VERSION").write_text(rev)


if __name__ == "__main__":
    main()
