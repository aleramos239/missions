"""fill.py TEMPLATE OUT REPO HOME: write the plist with __REPO__ and __HOME__ filled, XML-escaped."""
import sys
from xml.sax.saxutils import escape

tpl, out, repo, home = sys.argv[1:5]
text = open(tpl).read().replace("__REPO__", escape(repo)).replace("__HOME__", escape(home))
open(out, "w").write(text)
