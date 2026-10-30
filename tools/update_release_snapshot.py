"""Build-time public release metadata fallback. Never serialises credentials."""
import json
import os
from pathlib import Path
import urllib.request
import urllib.error


def main():
    headers={'Accept':'application/vnd.github+json','User-Agent':'LeadTheTarget-Pages'}
    if os.environ.get('GH_TOKEN'):headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    req=urllib.request.Request('https://api.github.com/repos/Leaferd6712/Lead-the-Target/releases/latest',headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as response:data=json.load(response)
    except urllib.error.HTTPError as error:
        if error.code!=404:raise
        data={'unavailable':True}
    (Path(__file__).resolve().parents[1]/'website'/'release.json').write_text(json.dumps(data),encoding='utf-8')


if __name__=='__main__':main()
