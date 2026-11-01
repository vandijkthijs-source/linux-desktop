#!/bin/sh

# Wait for XFCE and Polybar to initialize
sleep 8

cd "$HOME/.local/share/panel-pup" || exit 1

exec /usr/bin/python3 panel_pup.py \
  >> "$HOME/.cache/panel-pup.log" 2>&1
