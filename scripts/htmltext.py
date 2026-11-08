"""Plain-text rendering of the small HTML fragments used in the compilation.

Rules: tags are removed; <sup>x</sup> becomes ^x (or ^(xy) for more than one
character); <sub> content is kept inline; <br> becomes a space; character
references are decoded; non-breaking spaces become ordinary spaces; runs of
whitespace collapse to one space.
"""
import html
import re
from html.parser import HTMLParser


class _R(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.out.append(" ")
            return
        self.stack.append((tag, len(self.out)))

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.out.append(" ")

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] == tag:
                _, pos = self.stack[k]
                del self.stack[k:]
                if tag == "sup":
                    inner = "".join(self.out[pos:]).strip()
                    del self.out[pos:]
                    self.out.append("^" + inner if len(inner) <= 1 else "^(" + inner + ")")
                return

    def handle_data(self, data):
        self.out.append(data)


def to_text(s):
    if s is None:
        return None
    if "<" not in s and "&" not in s:
        t = s
    else:
        p = _R()
        p.feed(s)
        p.close()
        t = "".join(p.out)
        t = html.unescape(t)
    t = t.replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()
