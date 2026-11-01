#!/usr/bin/python3
"""Compact hover volume control with inline output selection."""
import json
import os
import subprocess
import sys
import threading
import socket
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango
from audio_outputs import outputs, snapshot, select

x, y, value = map(int, sys.argv[1:4])
server_mode = '--server' in sys.argv
screen_left = int(os.environ.get('POLYBAR_VOLUME_SCREEN_LEFT', '0'))
screen_width = int(os.environ.get('POLYBAR_VOLUME_SCREEN_WIDTH', Gdk.Screen.get_default().get_width()))
volume_timer = None
socket_path = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / 'polybar-volume-popup.sock'
server = None
css = Gtk.CssProvider()
css.load_from_path(str(Path(__file__).resolve().parent.parent / 'config/volume.css'))
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
win = Gtk.Window(type=Gtk.WindowType.POPUP)
win.set_wmclass('linux-panel-volume', 'Yad')
win.set_title('Panel Volume')
win.set_decorated(False)
win.set_resizable(False)
win.set_keep_above(True)
win.set_skip_taskbar_hint(True)
win.set_skip_pager_hint(True)
win.set_accept_focus(False)
win.set_type_hint(Gdk.WindowTypeHint.DROPDOWN_MENU)
win.set_default_size(280, 150)
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
box.set_margin_top(12); box.set_margin_bottom(12)
box.set_margin_start(12); box.set_margin_end(12)
scale = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1)
scale.set_inverted(True)
scale.set_draw_value(False)
scale.set_value(value)
scale.set_size_request(-1, 110)
def apply_volume():
    global volume_timer
    volume_timer = None
    value = round(scale.get_value())
    subprocess.Popen(['wpctl', 'set-volume', '-l', '1.0', '@DEFAULT_AUDIO_SINK@', f'{value}%'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if value > 0:
        subprocess.Popen(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', '0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return False


def change_volume(widget):
    global volume_timer
    if not server_mode:
        print(round(widget.get_value()), flush=True)
    else:
        if volume_timer: GLib.source_remove(volume_timer)
        volume_timer = GLib.timeout_add(35, apply_volume)


volume_handler = scale.connect('value-changed', change_volume)
box.pack_start(scale, False, False, 0)
box.pack_start(Gtk.Separator(), False, False, 0)
heading = Gtk.Label(label='Geluid afspelen via')
heading.set_xalign(0)
box.pack_start(heading, False, False, 0)
rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
scroll = Gtk.ScrolledWindow()
scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
scroll.set_propagate_natural_height(True)
scroll.set_max_content_height(190)
scroll.add(rows)
box.pack_start(scroll, False, False, 0)
status = Gtk.Label(label='Uitgangen laden…')
status.set_line_wrap(True)
status.set_max_width_chars(30)
status.set_xalign(0)
box.pack_start(status, False, False, 0)
win.add(box)
busy = False
signature = None
geometry_file = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / 'polybar-volume-popup.geometry'


def geometry(*_args):
    px, py = win.get_position()
    width, height = win.get_size()
    desired = max(screen_left, min(x, screen_left + screen_width - width))
    if px != desired:
        win.move(desired, y)
        px = desired
    temporary = geometry_file.with_suffix('.new')
    temporary.write_text(json.dumps([px, py, width, height]))
    temporary.replace(geometry_file)
    return False


def loaded(options, error=None, volume=None):
    global busy, signature
    busy = False
    rows.set_sensitive(True)
    if error:
        status.set_text(error)
        status.show()
        return False
    new_signature = [(o['key'], o['label'], o['active'], o['available']) for o in options]
    if new_signature != signature:
        signature = new_signature
        for child in rows.get_children(): rows.remove(child)
        for option in options:
            label = ('✓ ' if option['active'] else '') + option['label']
            if not option['available']: label += ' — niet aangesloten'
            button = Gtk.Button()
            text = Gtk.Label(label=label)
            text.set_xalign(0)
            text.set_ellipsize(Pango.EllipsizeMode.END)
            text.set_max_width_chars(31)
            button.add(text)
            button.set_tooltip_text(label)
            button.set_sensitive(option['available'])
            if option['active']: button.get_style_context().add_class('active-output')
            button.connect('clicked', choose, option)
            rows.pack_start(button, False, False, 0)
        rows.show_all()
    status.set_text('' if options else 'Geen geluidsuitgang beschikbaar')
    status.set_visible(not bool(options))
    if volume is not None:
        scale.handler_block(volume_handler)
        scale.set_value(volume)
        scale.handler_unblock(volume_handler)
    GLib.idle_add(geometry)
    return False


def worker(choice=None):
    try:
        if choice is not None: select(choice)
        options = outputs(snapshot())
        volume = float(subprocess.check_output(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'], text=True, timeout=2).split()[1]) * 100
        GLib.idle_add(loaded, options, None, min(100, round(volume)))
    except Exception as exc:
        print(str(exc), file=sys.stderr, flush=True)
        GLib.idle_add(loaded, [], 'Geluidsuitgang wijzigen mislukt' if choice else 'Uitgangen niet beschikbaar')


def choose(_button, option):
    global busy
    if busy: return
    busy = True
    rows.set_sensitive(False)
    status.set_text('Omschakelen…')
    status.show()
    threading.Thread(target=worker, args=(option,), daemon=True).start()


def refresh():
    global busy
    if win.get_visible() and not busy and not scale.get_state_flags() & Gtk.StateFlags.ACTIVE:
        busy = True
        threading.Thread(target=worker, daemon=True).start()
    return True


def command(message):
    global x, y, screen_left, screen_width
    if message.get('action') == 'show':
        x, y = int(message['x']), int(message['y'])
        screen_left = int(message['left'])
        screen_width = int(message['width'])
        win.move(x, y)
        win.show()
        geometry()
        refresh()
    elif message.get('action') == 'hide':
        win.hide()
    elif message.get('action') == 'quit':
        Gtk.main_quit()
    return False


def listen():
    while True:
        try:
            message = json.loads(server.recv(1024))
            GLib.idle_add(command, message)
        except (OSError, ValueError):
            return


win.connect('configure-event', geometry)
win.connect('destroy', Gtk.main_quit)
win.move(x, y)
if server_mode:
    box.show_all()
    win.realize()
else:
    win.show_all()
if server_mode:
    win.hide()
    socket_path.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(str(socket_path))
    os.chmod(socket_path, 0o600)
    threading.Thread(target=listen, daemon=True).start()
    # Cache available outputs before the first hover.
    busy = True
    threading.Thread(target=worker, daemon=True).start()
else:
    refresh()
GLib.timeout_add_seconds(2, refresh)
try:
    Gtk.main()
finally:
    if server is not None:
        server.close()
        socket_path.unlink(missing_ok=True)
