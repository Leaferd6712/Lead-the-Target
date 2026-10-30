"""Build, execute-test and package all three release formats. Windows / Python 3.12.

No asset is published by this script. CI publishes only after this exits cleanly.
"""
import argparse
import hashlib
import importlib.metadata
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def run(args,**kwargs):
    print('Running:',*map(str,args),flush=True)
    subprocess.run(list(map(str,args)),check=True,cwd=ROOT,**kwargs)


def smoke(executable,output,cwd=None):
    env=dict(os.environ)
    # The EXE cannot find this project's interpreter or Python DLL through PATH.
    env['PATH']=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32')
    env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
    subprocess.run([str(executable),'--headless','--level','1','--autoplay','--frames','160',
                    '--screenshot',str(output)],cwd=cwd or executable.parent,env=env,check=True,timeout=120)
    if not output.exists() or output.stat().st_size<3000:raise RuntimeError('Smoke test produced no valid screenshot')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',required=True)
    parser.add_argument('--iscc',type=Path,required=True)
    args=parser.parse_args();version=args.version.removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?',version):parser.error('Use a semantic version, e.g. 2.0.0')
    run([sys.executable,'-m','unittest','discover','-s','tests','-q'])
    licenses=ROOT/'assets'/'licenses';licenses.mkdir(exist_ok=True)
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt',licenses/'PYTHON-LICENSE.txt')
    for package,needle,destination in (('panda3d','LICENSE.txt','PANDA3D-LICENSE.txt'),
                                      ('pyinstaller','COPYING.txt','PYINSTALLER-COPYING.txt')):
        distribution=importlib.metadata.distribution(package)
        source_license=next(f for f in distribution.files if str(f).endswith(needle) and '.dist-info/' in str(f))
        shutil.copy2(distribution.locate_file(source_license),licenses/destination)
    out=ROOT/'release';out.mkdir(exist_ok=True)
    qa=ROOT/'artifacts'/'release-qa';qa.mkdir(parents=True,exist_ok=True)
    name=f'LeadTheTarget-v{version}'
    source=out/(name+'-source.zip')
    included=list(ROOT.glob('*.py'))+[ROOT/p for p in ('requirements.txt','README.md','ACCESSIBLE_GUIDE.md',
        'THIRD_PARTY_NOTICES.md','LICENSE','play.bat','VERSION')]
    included+=list((ROOT/'assets').rglob('*'))
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as z:
        for path in included:
            if path.is_file():z.write(path,Path(name+'-source')/path.relative_to(ROOT))
    extracted=qa/'source';extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(source) as z:z.extractall(extracted)
    run([sys.executable,extracted/(name+'-source')/'main.py','--headless','--level','1',
         '--autoplay','--frames','160','--screenshot',qa/'source.png'])
    destination=(ROOT/'dist'/'LeadTheTarget').resolve()
    if not destination.is_relative_to(ROOT.resolve()):raise RuntimeError('Build destination escaped the workspace')
    run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--log-level','WARN',
         '--name','LeadTheTarget','--icon',ROOT/'assets'/'app.ico','--add-data',f'{ROOT / "assets"};assets',
         '--collect-all','panda3d','--collect-all','direct','--exclude-module','pygame',
         '--workpath',ROOT/'artifacts'/'build','--specpath',ROOT/'artifacts',
         '--distpath',ROOT/'dist',ROOT/'main.py'])
    app=ROOT/'dist'/'LeadTheTarget'
    for path in ('README.md','ACCESSIBLE_GUIDE.md','THIRD_PARTY_NOTICES.md','LICENSE','VERSION'):
        shutil.copy2(ROOT/path,app/path)
    smoke(app/'LeadTheTarget.exe',qa/'portable.png')
    with zipfile.ZipFile(out/(name+'-windows-portable.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for path in app.rglob('*'):
            if path.is_file():z.write(path,Path('LeadTheTarget')/path.relative_to(app))
    run([args.iscc,'/Q',f'/DGameVersion={version}',f'/DSourceDir={app}',f'/DReleaseDir={out}',ROOT/'installer'/'game.iss'])
    installer=out/(name+'-windows-setup.exe')
    installed=qa/'installed'
    run([installer,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS',f'/DIR={installed}',f'/LOG={qa / "install.log"}'])
    smoke(installed/'LeadTheTarget.exe',qa/'installed.png')
    uninstaller=installed/'unins000.exe'
    if not uninstaller.exists():raise RuntimeError('Installer did not create an uninstaller')
    run([uninstaller,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/LOG={qa / "uninstall.log"}'])
    if (installed/'LeadTheTarget.exe').exists():raise RuntimeError('Uninstaller left the game executable behind')
    assets=[source,out/(name+'-windows-portable.zip'),installer]
    for p in assets:
        if not p.exists() or not p.stat().st_size:raise RuntimeError(f'Missing distribution: {p}')
    (out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in assets),encoding='utf-8')
    print('All three distributions built and execution-tested.',flush=True)


if __name__=='__main__':main()
