from html.parser import HTMLParser

class DivStackParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            attrs_dict = dict(attrs)
            self.stack.append((self.getpos()[0], attrs_dict.get('id', attrs_dict.get('class', ''))))

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.stack:
                self.stack.pop()
            else:
                print(f'EXTRA </div> at line {self.getpos()[0]}')

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start = -1
for i, line in enumerate(lines):
    if 'id="page-upload"' in line:
        start = i
        break

end = -1
for i, line in enumerate(lines[start:]):
    if 'id="page-rules"' in line:
        end = start + i
        break

content = ''.join(lines[start:end])
parser = DivStackParser()
parser.feed(content)
for line, identity in parser.stack:
    print(f'UNCLOSED <div> at line {line}: {identity}')
