"""Fast structural checks with no third-party dependency. Browser QA is separate."""
from html.parser import HTMLParser
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'website'


class Inspect(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.links=[];self.formats=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='img':
            assert 'alt' in a,'An image is missing alt text'
            assert (ROOT/a['src']).is_file(),f'Missing screenshot: {a["src"]}'
        if tag=='a':
            self.links.append(a.get('href',''))
            if 'data-format' in a:self.formats.add(a['data-format'])
        if tag in ('script','link'):
            path=a.get('src') or a.get('href')
            if path and not path.startswith('http'):assert (ROOT/path).is_file(),f'Missing asset: {path}'


def main():
    p=Inspect();p.feed((ROOT/'index.html').read_text(encoding='utf-8'))
    assert p.formats=={'source','portable','setup'}
    for href in p.links:
        if href.startswith('#') and len(href)>1:assert href[1:] in p.ids,f'Broken anchor: {href}'
    js=(ROOT/'downloads.js').read_text()
    for suffix in ('-source.zip','-windows-portable.zip','-windows-setup.exe'):assert suffix in js
    assert 'release.draft' in js and 'release.prerelease' in js
    for font in ('Barlow-Regular.ttf','Barlow-SemiBold.ttf','OFL.txt'):assert (ROOT/'fonts'/font).exists()
    print('Website structure, screenshots, fonts, anchors and stable-release wiring passed.')


if __name__=='__main__':main()
