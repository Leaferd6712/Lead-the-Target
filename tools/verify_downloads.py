"""Download the public stable assets, verify hashes and execute the downloaded copies.

Windows maintainer check. Installs only into this project's artifacts/download-qa.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
QA=(ROOT/'artifacts'/'download-qa').resolve()


def download(url,path):
    print('Download:',url,flush=True)
    req=urllib.request.Request(url,headers={'User-Agent':'LeadTheTarget-release-QA'})
    with urllib.request.urlopen(req,timeout=120) as source,path.open('wb') as out:
        while block:=source.read(1024*1024):out.write(block)


def extract(archive,destination):
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if not (destination/name).resolve().is_relative_to(destination.resolve()):raise RuntimeError('Unsafe archive path')
        z.extractall(destination)


def execute(command,**kwargs):
    subprocess.run([str(x) for x in command],check=True,timeout=180,**kwargs)


def main():
    assert QA.is_relative_to(ROOT.resolve())
    QA.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request('https://api.github.com/repos/Leaferd6712/Lead-the-Target/releases/latest',headers={'User-Agent':'LeadTheTarget-release-QA'})
    with urllib.request.urlopen(req,timeout=30) as response:release=json.load(response)
    assert not release['draft'] and not release['prerelease']
    tag=release['tag_name'];assets={a['name']:a for a in release['assets']}
    names={k:f'LeadTheTarget-{tag}{suffix}' for k,suffix in
           (('source','-source.zip'),('portable','-windows-portable.zip'),('setup','-windows-setup.exe'))}
    for name in list(names.values())+['SHA256SUMS.txt']:
        assert name in assets and assets[name]['size']>0
        url=assets[name]['browser_download_url']
        assert url.startswith(f'https://github.com/Leaferd6712/Lead-the-Target/releases/download/{tag}/')
        download(url,QA/name)
    sums=dict(line.split('  ',1)[::-1] for line in (QA/'SHA256SUMS.txt').read_text().splitlines())
    for name in names.values():assert hashlib.sha256((QA/name).read_bytes()).hexdigest()==sums[name]
    print('All three public assets match SHA256SUMS.',flush=True)
    extract(QA/names['source'],QA/'source')
    source=next((QA/'source').glob('*/main.py'))
    venv=QA/'clean-source-env'
    execute([sys.executable,'-m','venv',venv])
    python=venv/'Scripts'/'python.exe'
    execute([python,'-m','pip','install','-r',source.parent/'requirements.txt'])
    execute([python,source,'--headless','--level','1','--autoplay','--frames','160','--screenshot',QA/'source.png'])
    extract(QA/names['portable'],QA/'portable')
    exe=QA/'portable'/'LeadTheTarget'/'LeadTheTarget.exe'
    env={**os.environ,'PATH':str(Path(os.environ['SystemRoot'])/'System32')}
    env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
    execute([exe,'--headless','--level','34','--autoplay','--frames','360','--screenshot',QA/'portable.png'],env=env)
    execute([exe,'--level','1','--frames','15','--screenshot',QA/'portable-opengl.png'],env=env)
    installed=QA/'installed'
    group=f'LeadTheTarget Public Download QA {tag}'
    execute([QA/names['setup'],'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/DIR={installed}',f'/GROUP={group}',f'/LOG={QA / "install.log"}'])
    shortcut=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs'/group/'Lead the Target.lnk'
    assert shortcut.exists(),'Installed shortcut missing'
    execute([installed/'LeadTheTarget.exe','--headless','--level','1','--frames','160','--screenshot',QA/'installed.png'],env=env)
    execute([installed/'unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/LOG={QA / "uninstall.log"}'])
    assert not (installed/'LeadTheTarget.exe').exists() and not shortcut.exists()
    for image in ('source.png','portable.png','portable-opengl.png','installed.png'):
        assert (QA/image).stat().st_size>3000
    (QA/'result.json').write_text(json.dumps({'tag':tag,'release':release['html_url'],'checks':'All public distributions downloaded, hashed and execution-tested.'},indent=2))
    print('PUBLIC DOWNLOAD VERIFICATION PASSED:',tag,flush=True)


if __name__=='__main__':main()
