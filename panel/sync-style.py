#!/usr/bin/python3
"""Regenerate popup colors from the Polybar palette after a palette change."""
from pathlib import Path
import configparser,re
r=Path(__file__).resolve().parent
c=configparser.ConfigParser(interpolation=None);c.read(r/'config/polybar/config.ini')
p=dict(c['colors'])
for key in ['background','panel','selected','foreground','muted','accent','success','border']:
 if not re.fullmatch(r'#[0-9a-fA-F]{6}',p[key]): raise ValueError('Expected RGB color: '+key)
(r/'config/rofi/panel.rasi').write_text('* {\n'+''.join(f'    {name}: {p[key]};\n' for name,key in [('bg','background'),('panel','panel'),('selected','selected'),('fg','foreground'),('muted','muted'),('accent','accent'),('success','success'),('border','border')])+'    background-color: transparent;\n    text-color: @fg;\n}\n')
(r/'config/volume.css').write_text('''window, window.background, window box, window grid, window scale {
  background-color: %(background)s;
  background-image: none;
  color: %(foreground)s;
  font-family: "DejaVu Sans";
  font-size: 10pt;
  border-radius: 0;
  box-shadow: none;
  border: none;
}
window.background {
  border: 1px solid %(border)s;
}
scale trough {
  background-color: %(panel)s;
  min-width: 6px;
  border-radius: 0;
}
scale trough highlight {
  background-color: %(accent)s;
  border-radius: 0;
}
scale slider {
  background-color: %(foreground)s;
  min-width: 12px;
  min-height: 12px;
  border-radius: 0;
  border: none;
}
scale slider:hover, scale slider:active {
  background-color: %(accent)s;
}

button {
  background-image: none;
  background-color: %(panel)s;
  color: %(foreground)s;
  border: 1px solid %(border)s;
  border-radius: 0;
  padding: 7px 9px;
  box-shadow: none;
}
button:hover, button.active-output { background-color: %(selected)s; }
button.active-output { border-color: %(accent)s; }
button:disabled { color: %(muted)s; }
label { color: %(foreground)s; }
separator { background-color: %(border)s; min-height: 1px; }
'''%p)
print('Popup styles generated from Polybar colors.')
