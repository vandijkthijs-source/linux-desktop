#!/usr/bin/env python3
"""Back up destinations and link the reviewed project files into the desktop."""
from pathlib import Path
from datetime import datetime
import shutil
import json
ROOT=Path(__file__).resolve().parent
HOME=Path.home()

def main():
    backup=ROOT/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    mapping={}
    for source in (ROOT/'scripts').iterdir():
        if source.is_file() and source.suffix != '.py': mapping[source]=HOME/'.local/bin'/source.name
    for folder in ['polybar','rofi']:
        for source in (ROOT/'config'/folder).iterdir():
            if source.name == 'volume-hover-x': continue
            mapping[source]=HOME/'.config'/folder/source.name
    # Pup autostart is only a reference, not managed by this project.
    source=ROOT/'config/autostart/polybar-volume-hover.desktop'
    mapping[source]=HOME/'.config/autostart'/source.name
    manifest=[]
    for src,dest in mapping.items():
        if dest.is_symlink() and dest.resolve()==src: continue
        previous=backup/dest.relative_to(HOME)
        existed=dest.exists() or dest.is_symlink()
        if existed:
            previous.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(dest,previous,follow_symlinks=False)
        manifest.append({'destination':str(dest),'backup':str(previous) if existed else None})
        backup.mkdir(parents=True,exist_ok=True)
        (backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
        dest.parent.mkdir(parents=True,exist_ok=True)
        temp=dest.with_name(dest.name+'.linux-panel-new')
        temp.symlink_to(src)
        temp.replace(dest)
    print('Installed project links. Backup: '+str(backup) if manifest else 'All project links already installed.')

if __name__=='__main__': main()
