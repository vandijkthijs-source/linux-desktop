"""Find the volume icon by its configured accent in the actual Polybar window.

The volume prefix must retain a unique accent on the right half of the bar,
including when muted. No desktop screenshot is captured or saved.
"""
import configparser
import subprocess
import gi
gi.require_version('Gdk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gdk, GdkX11, Pango, PangoCairo
from pathlib import Path
from PIL import Image, ImageChops

def locate_regions():
    cfg = configparser.ConfigParser(interpolation=None, strict=False)
    cfg.read(Path.home() / '.config/polybar/config.ini')
    color = cfg['colors']['accent'].strip().lstrip('#')[-6:]
    rgb = tuple(bytes.fromhex(color))
    ids = subprocess.run(['xdotool', 'search', '--onlyvisible', '--class', 'Polybar'], capture_output=True, text=True, timeout=2).stdout.split()
    display = Gdk.Display.get_default()
    for xid in ids:
        win = GdkX11.X11Window.foreign_new_for_display(display, int(xid))
        if win is None: continue
        width, height = win.get_width(), win.get_height()
        if height > 100 or width < 200: continue
        image = Gdk.pixbuf_get_from_window(win, 0, 0, width, height)
        if image is None: continue
        data, stride, channels = image.get_pixels(), image.get_rowstride(), image.get_n_channels()
        # Calculate the color mask in native image code so icon tracking cannot
        # stall pointer checks while Python visits every screenshot pixel.
        mode = 'RGBA' if channels == 4 else 'RGB'
        pixels = Image.frombytes(mode, (image.get_width(), height), bytes(data), 'raw', mode, stride).convert('RGB')
        def color_columns(color):
            difference = ImageChops.difference(pixels, Image.new('RGB', pixels.size, color))
            masks = [band.point([255 if value <= 8 else 0 for value in range(256)]) for band in difference.split()]
            mask = ImageChops.multiply(ImageChops.multiply(masks[0], masks[1]), masks[2])
            projection = mask.resize((pixels.width, 1), Image.Resampling.BOX).tobytes()
            return [x for x, value in enumerate(projection) if value >= round(2 * 255 / height)]
        columns = [x for x in color_columns(rgb) if x >= width//2]
        if not columns: continue
        # The volume icon is the first accent-colored cluster in the right block.
        start = columns[0]; end = start
        for x in columns[1:]:
            if x-end > 6: break
            end=x
        _, bx, by = win.get_origin()
        regions = {'volume': (bx+start-5, bx+end+40, by, by+height, bx, width)}
        flock_columns=[x for x in color_columns((199,186,148)) if x < width//2]
        if flock_columns:
            first=flock_columns[0]
            layout=Pango.Layout.new(PangoCairo.FontMap.get_default().create_context())
            layout.set_font_description(Pango.FontDescription('DejaVu Sans 10'))
            layout.set_text('Flock: OFF',-1)
            label_width=layout.get_pixel_size()[0]
            regions['flock']=(bx+first-5,bx+first+label_width+5,by,by+height,bx,width)
        muted = tuple(bytes.fromhex(cfg['colors']['muted'].strip().lstrip('#')[-6:]))
        before_volume = [x for x in color_columns(muted) if x < start - 5]
        if before_volume:
            bt_start = before_volume[-1]
            for x in reversed(before_volume[:-1]):
                if bt_start-x > 6: break
                bt_start = x
            regions['bluetooth'] = (bx+bt_start-5, bx+start-10, by, by+height, bx, width)
            green = tuple(bytes.fromhex(cfg['colors']['success'].strip().lstrip('#')[-6:]))
            wifi_columns = [x for x in color_columns(green) if x < bt_start-5]
            if wifi_columns:
                regions['wifi'] = (bx+wifi_columns[0]-5, bx+bt_start-10, by, by+height, bx, width)
        return regions
    return {}


def locate():
    return locate_regions().get('volume')
