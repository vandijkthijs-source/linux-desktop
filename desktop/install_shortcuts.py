#!/usr/bin/env python3
"""Create Word/PowerPoint web, Chrome and Immich shortcuts with official icons."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
from urllib.request import urlopen
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ICONS = {
    'word': 'https://static2.sharepointonline.com/files/fabric/assets/brand-icons/product/svg/word_48x1.svg',
    'powerpoint': 'https://static2.sharepointonline.com/files/fabric/assets/brand-icons/product/svg/powerpoint_48x1.svg',
    'immich': 'https://raw.githubusercontent.com/immich-app/immich/main/design/immich-logo.svg',
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--immich-url', default='http://localhost:2283/photos')
    parser.add_argument('--offline', action='store_true', help='Use installed theme icons instead of downloading official SVG files')
    parser.add_argument('--trust', action='store_true', help='Mark shortcuts trusted in the current graphical user session')
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    if args.trust and home != Path.home().resolve():
        parser.error('--trust only applies to the current user')
    parsed = urlparse(args.immich_url)
    if parsed.scheme not in ['http', 'https'] or any(x in args.immich_url for x in '\n\r'):
        parser.error('--immich-url must be an HTTP(S) URL')
    if home == Path.home().resolve():
        desktop = Path(subprocess.check_output(['xdg-user-dir', 'DESKTOP'], text=True).strip())
    else:
        desktop = home / 'Desktop'
    icons = home / '.local/share/icons/desktop-web'
    backup = home / '.local/state/desktop-shortcut-backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    def write(path, data):
        if path.exists():
            old = backup / path.relative_to(home)
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, old)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    chosen = {'word': 'application-msword', 'powerpoint': 'application-vnd.ms-powerpoint', 'immich': 'folder-pictures'}
    if not args.offline:
        # Download all assets before writing any files.
        assets = {}
        for name, url in ICONS.items():
            with urlopen(url, timeout=25) as response:
                data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024 or not ET.fromstring(data).tag.endswith('svg'):
                raise ValueError(f'Invalid icon: {name}')
            assets[name] = data
        for name, data in assets.items():
            path = icons / f'{name}.svg'
            write(path, data)
            chosen[name] = str(path)
    for name, icon, url in [
        ('Word', chosen['word'], 'https://word.cloud.microsoft/'),
        ('PowerPoint', chosen['powerpoint'], 'https://powerpoint.cloud.microsoft/'),
        ('Immich', chosen['immich'], args.immich_url),
    ]:
        # Desktop Exec quoting is distinct from shell quoting.
        escaped = url.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
        path = desktop / f'{name}.desktop'
        write(path, (f'[Desktop Entry]\nType=Application\nName={name}\nExec=xdg-open "{escaped}"\nIcon={icon}\nTerminal=false\n').encode())
        path.chmod(0o755)
    chrome = Path('/usr/share/applications/google-chrome.desktop')
    if chrome.exists():
        path = desktop / 'Google-Chrome.desktop'
        write(path, chrome.read_bytes())
        path.chmod(0o755)
    if args.trust:
        for name in ['Word', 'PowerPoint', 'Immich', 'Google-Chrome']:
            path = desktop / f'{name}.desktop'
            if path.exists():
                subprocess.run(['gio', 'set', str(path), 'metadata::trusted', 'true'], check=True)
    print('Shortcuts:', desktop)
    print('Existing files, if any, backed up under:', backup)

if __name__ == '__main__':
    main()
