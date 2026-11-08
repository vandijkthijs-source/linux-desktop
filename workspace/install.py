#!/usr/bin/env python3
"""Copy cube/menu files; changing Compiz or login startup requires explicit flags."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
REQUIRED = ['core', 'composite', 'opengl', 'compiztoolbox', 'decor', 'regex',
            'imgpng', 'move', 'resize', 'place', 'snap', 'grid', 'cube', 'rotate',
            'cubeaddon', 'scale', 'expo', 'workarounds', 'commands', 'blur']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--configure', action='store_true', help='Apply cube and Alt+Tab settings to the current user')
    parser.add_argument('--autostart', action='store_true', help='Enable cube at login; requires --configure')
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    if args.autostart and not args.configure:
        parser.error('--autostart requires --configure')
    if args.configure and home != Path.home().resolve():
        parser.error('--configure can only change the current user profile')
    context = None
    settings = json.loads((ROOT / 'cube-settings.json').read_text())
    if args.configure:
        import compizconfig
        context = compizconfig.Context()
        if context.CurrentBackend.Name != 'ini':
            parser.error('This configuration/backup workflow requires the Compiz INI backend')
        missing = [p for p in REQUIRED if p not in context.Plugins]
        if missing:
            parser.error('Missing Compiz plugins: ' + ', '.join(missing))
        for plugin, values in settings.items():
            for key in values:
                if key not in context.Plugins[plugin].Screen:
                    parser.error(f'Missing Compiz setting: {plugin}/{key}')
        commands = context.Plugins['commands'].Screen
        slots = [i for i in range(12) if commands[f'command{i}'].Value.startswith(str(home / '.local/bin/desktop-alt-tab'))]
        slots += [i for i in range(12) if not commands[f'command{i}'].Value and i not in slots]
        if len(slots) < 2:
            parser.error('Two unused Compiz command slots are required')
    backup = home / '.local/state/desktop-cube-backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    manifest = []
    def put(source, destination, text=None):
        old = None
        if destination.exists() or destination.is_symlink():
            old = backup / destination.relative_to(home)
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, old, follow_symlinks=False)
        manifest.append({'destination': str(destination), 'backup': str(old) if old else None})
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            destination.unlink()
        if text is None:
            shutil.copy2(source, destination)
        else:
            destination.write_text(text)
    if context:
        profile = home / '.config/compiz-1'
        if profile.exists():
            shutil.copytree(profile, backup / 'compiz-1')
    for name in ['desktop-alt-tab', 'desktop-cube-session']:
        put(ROOT / name, home / '.local/bin' / name)
    put(ROOT / 'alt-tab-icons.rasi', home / '.config/rofi/alt-tab-icons.rasi')
    if context:
        old_plugins = context.Plugins['core'].Screen['active_plugins'].Value
        plugins = REQUIRED + [p for p in old_plugins if p not in REQUIRED + ['wall', 'switcher', 'staticswitcher', 'session']]
        context.Plugins['core'].Screen['active_plugins'].Value = plugins
        for plugin, values in settings.items():
            for key, value in values.items():
                context.Plugins[plugin].Screen[key].Value = value
        command = str(home / '.local/bin/desktop-alt-tab')
        # Shell-quote the executable for homes containing spaces or punctuation.
        import shlex
        for slot, key, suffix in [(slots[0], '<Alt>Tab', ''), (slots[1], '<Shift><Alt>Tab', ' --reverse')]:
            commands[f'command{slot}'].Value = shlex.quote(command) + suffix
            commands[f'run_command{slot}_key'].Value = key
        context.Write()
    if args.autostart:
        command = str(home / '.local/bin/desktop-cube-session').replace('\\', '\\\\').replace('"', '\\"')
        put(None, home / '.config/autostart/desktop-cube.desktop',
            '[Desktop Entry]\nType=Application\nName=Desktop Cube\n'
            f'Exec="{command}"\nOnlyShowIn=XFCE;\nTerminal=false\nX-GNOME-Autostart-enabled=true\n')
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Installed cube/menu files. No window manager was started or restarted.')
    print('Backup:', backup)
    if not args.configure:
        print('Compiz settings unchanged. Use --configure to apply cube/menu settings.')

if __name__ == '__main__':
    main()
