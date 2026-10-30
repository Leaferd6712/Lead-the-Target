"""Real Chromium responsive and download-state checks. Developer dependency: playwright.

Run against a local or deployed URL. Actual release links are asserted when live.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('--live',action='store_true')
    p.add_argument('--tag',help='Require this stable release in every download link');args=p.parse_args()
    out=Path(__file__).resolve().parents[1]/'artifacts'/'website';out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as runtime:
        browser=runtime.chromium.launch(headless=True)
        page=browser.new_page()
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        for width,height in ((1440,1000),(768,1024),(390,844)):
            page.set_viewport_size({'width':width,'height':height})
            page.goto(args.url,wait_until='networkidle')
            page.locator('#release-status').wait_for()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Horizontal overflow at {width}'
            assert page.locator('h1').inner_text()=='Outthink\nthe convoy.'
            page.locator('img').evaluate_all('(images)=>images.forEach(i=>i.loading="eager")')
            page.wait_for_function('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)')
            if args.live:
                page.wait_for_function("document.querySelectorAll('[data-format][href]').length===3",timeout=20000)
                for format,suffix in (('source','-source.zip'),('portable','-windows-portable.zip'),('setup','-windows-setup.exe')):
                    button=page.locator(f'[data-format="{format}"]')
                    assert button.get_attribute('href').endswith(suffix)
                    assert button.get_attribute('aria-disabled') is None
                    if args.tag:assert f'/download/{args.tag}/' in button.get_attribute('href')
                if args.tag:assert args.tag in page.locator('#release-status').inner_text()
            page.screenshot(path=str(out/f'{width}.png'),full_page=True)
            print(f'{width}x{height}: layout, imagery, scripts'+(', live downloads' if args.live else '')+' passed')
        assert not errors,errors
        if not args.live:
            # A malformed release must leave every download disabled.
            page.route('**/releases/latest',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps({'tag_name':'v9.9.9','draft':False,'prerelease':False,'assets':[]})))
            page.route('**/release.json',lambda route:route.fulfill(status=404,body='{}'))
            page.reload(wait_until='networkidle')
            assert page.locator('[data-format][aria-disabled="true"]').count()==3
            assert page.locator('[data-format][href]').count()==0
            print('Incomplete release: all download actions correctly disabled')
        browser.close()


if __name__=='__main__':main()
