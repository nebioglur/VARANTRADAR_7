import re
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.errors = []
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.void_tags:
            self.tags.append((tag.lower(), self.getpos()))

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in self.void_tags:
            return
        if not self.tags:
            self.errors.append(f"Unexpected closing tag </{t}> at {self.getpos()}")
            return
        # Find matching tag from top
        for i in range(len(self.tags) - 1, -1, -1):
            if self.tags[i][0] == t:
                # Unclosed tags between
                for unclosed, pos in self.tags[i+1:]:
                    if unclosed not in {'p', 'li', 'td', 'th', 'tr'}:
                        self.errors.append(f"Unclosed <{unclosed}> from {pos} closed by </{t}> at {self.getpos()}")
                self.tags = self.tags[:i]
                return
        self.errors.append(f"Closing tag </{t}> at {self.getpos()} without match")

with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

parser = MyHTMLParser()
parser.feed(html)
print(f"Total HTML errors: {len(parser.errors)}")
for e in parser.errors[:20]:
    print(" ", e)
