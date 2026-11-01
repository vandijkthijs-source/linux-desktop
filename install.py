#!/usr/bin/env python3
"""Install local desktop sources, preserving user settings and backing up writes."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel',action='store_true',help='Install the full example Polybar/Rofi configuration')
    parser.add_argument('--home',type=Path,default=Path.home(),help='Target home, useful for isolated installation tests')
    args=parser.parse_args();home=args.home.expanduser().resolve()
    panel=home/'.local/share/linux-desktop/panel'
    backup=home/'.local/state/linux-desktop/backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    manifest=[]
    def put(src,dest,text=None):
        if dest.exists() or dest.is_symlink():
            old=backup/dest.relative_to(home);old.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(dest,old,follow_symlinks=False)
            manifest.append({'destination':str(dest),'backup':str(old)})
        else:manifest.append({'destination':str(dest),'backup':None})
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.is_symlink():dest.unlink()
        if text is None:shutil.copy2(src,dest)
        else:dest.write_text(text)
    for source in (ROOT/'panel').rglob('*'):
        if not source.is_file() or '__pycache__' in source.parts:continue
        text=source.read_text().replace('@HOME@',str(home)).replace('@PANEL_DIR@',str(panel))
        dest=panel/source.relative_to(ROOT/'panel');put(source,dest,text);shutil.copymode(source,dest)
    for folder,dest in [('boids',home/'.local/share/desktop-boids'),('panel-pup',home/'.local/share/panel-pup')]:
        for source in (ROOT/folder).iterdir():
            if source.is_file() and source.name!='config.example.json':put(source,dest/source.name)
    config=home/'.local/share/panel-pup/config.json'
    if not config.exists():put(ROOT/'panel-pup/config.example.json',config)
    for name in ('flock-control','panel-pup-control'):
        put(panel/'scripts'/name,home/'.local/bin'/name)
    for name,command in [('desktop-boids',f'/usr/bin/python3 "{home}/.local/share/desktop-boids/boids.py"'),('panel-pup',f'"{home}/.local/share/panel-pup/start.sh"')]:
        dest=home/'.config/autostart'/f'{name}.desktop'
        put(None,dest,f'[Desktop Entry]\nType=Application\nName={name}\nExec={command}\nTerminal=false\n')
    if args.panel:
        # This installer derives HOME itself, so run it with the requested home.
        import os
        env=dict(os.environ,HOME=str(home))
        subprocess.run([sys.executable,str(panel/'install.py')],env=env,check=True)
        put(panel/'config/autostart/polybar.desktop',home/'.config/autostart/polybar.desktop')
    backup.mkdir(parents=True,exist_ok=True)
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Installed apps and controls. No desktop processes were restarted.')
    print('Backup manifest:',backup/'manifest.json')
    if not args.panel:print('Panel config unchanged. Use --panel to install the full example panel and hover integration.')
    print('Download Pup artwork before starting it: bash ~/.local/share/panel-pup/download_assets.sh brown')
if __name__=='__main__':main()
