from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        pass
    def handle_endtag(self, tag):
        pass
    def handle_data(self, data):
        pass

parser = MyHTMLParser()
try:
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        parser.feed(f.read())
    print("HTML Parsing successful")
except Exception as e:
    print("HTML Parsing error:", e)
