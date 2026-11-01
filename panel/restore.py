#!/usr/bin/env python3
"""Restore an install backup: python3 restore.py backups/TIMESTAMP"""
import json, sys, shutil
from pathlib import Path
root=Path(sys.argv[1]).resolve()
for row in reversed(json.loads((root/'manifest.json').read_text())):
    dest=Path(row['destination'])
    if dest.exists() or dest.is_symlink(): dest.unlink()
    if row['backup']: shutil.copy2(row['backup'],dest,follow_symlinks=False)
print('Restored. Reload Polybar and the volume watcher to use restored files.')
