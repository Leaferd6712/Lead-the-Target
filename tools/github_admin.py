"""Maintainer helper: authenticated GitHub API without printing credentials.

Uses the existing Git credential manager. No tokens are stored in this project.
Not shipped with the game; Actions uses its short-lived GITHUB_TOKEN instead.
"""
import argparse
import json
from pathlib import Path
import subprocess
import urllib.request
import urllib.error


def request(endpoint,method='GET',data=None):
    credential=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',
                              text=True,capture_output=True,check=True)
    fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
    token=fields.get('password')
    if not token:raise RuntimeError('GitHub credential manager has no credential')
    url='https://api.github.com/'+endpoint.lstrip('/')
    body=json.dumps(data).encode() if data is not None else None
    req=urllib.request.Request(url,body,method=method,headers={
        'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
        'X-GitHub-Api-Version':'2022-11-28','User-Agent':'LeadTheTarget-release-maintainer',
        'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as response:
        content=response.read()
        return json.loads(content) if content else {'status':response.status}


def main():
    p=argparse.ArgumentParser();p.add_argument('endpoint');p.add_argument('--method',default='GET')
    p.add_argument('--data',type=Path);p.add_argument('--fields',help='Comma-separated fields to print')
    a=p.parse_args()
    try:result=request(a.endpoint,a.method,json.loads(a.data.read_text()) if a.data else None)
    except urllib.error.HTTPError as error:
        print(f'GitHub API {error.code}: {error.read().decode()[:1200]}');return 1
    if a.fields:
        keys=a.fields.split(',')
        if isinstance(result,list):result=[{k:row.get(k) for k in keys} for row in result]
        else:result={k:result.get(k) for k in keys}
    print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
