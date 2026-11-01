#!/usr/bin/env python3
"""Panel Pup: reversible, interactive, transparent X11 top-bar dog pet.

Source code MIT; original dog GIFs are separately licensed CC BY-ND 4.0.
Run from a terminal; this does not alter Polybar, XFCE, or startup files.
"""
from __future__ import annotations
import ctypes
import ctypes.util
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

from behavior import PetBehavior, PointerResistance

ROOT = Path(__file__).resolve().parent


def load_config(path):
    with open(path, encoding="utf8") as f:
        cfg = json.load(f)
    for k in ("left", "right", "bar_top", "bar_height", "pet_height"):
        cfg[k] = int(cfg[k])
    cfg["speed"] = float(cfg["speed"])
    cfg["sleep_after"] = float(cfg["sleep_after"])
    if cfg["bar_height"] <= 0 or cfg["pet_height"] <= 0:
        raise ValueError("Heights must be positive")
    if not (0 < cfg["speed"] <= 500):
        raise ValueError("speed must be between 0 and 500")
    if cfg["color"] not in {"brown", "black", "white", "red", "akita"}:
        raise ValueError("color must be brown, black, white, red or akita")
    for k in ("on_click", "on_double_click", "on_middle_click"):
        if cfg[k] not in {"react", "hop", "nap", "walk", "run", "pause", "resume"}:
            raise ValueError(f"Invalid action for {k}")
    return cfg


def assets_for(cfg, asset_dir):
    names = {"idle": "idle", "walk": "walk", "run": "run", "sleep": "lie", "react": "swipe"}
    paths = {state: asset_dir / f'{cfg["color"]}_{name}_8fps.gif'
            for state, name in names.items()}
    basket = {state: asset_dir / f'{cfg["color"]}_{state}.gif'
              for state in ("basket_enter", "basket_rest", "basket_exit")}
    if all(path.is_file() for path in basket.values()):
        paths.update(basket)
    return paths


def main():
    p = argparse.ArgumentParser(description="Dog living in a small top bar walking area")
    p.add_argument("--config", default=str(ROOT / "config.json"), help="JSON config")
    p.add_argument("--assets", default=str(ROOT / "assets"), help="Directory with original GIFs")
    p.add_argument("--check", action="store_true", help="Validate config and sprites without opening GUI")
    args = p.parse_args()
    cfg = load_config(args.config)
    paths = assets_for(cfg, Path(args.assets))
    missing = [path for path in paths.values() if not path.is_file()]
    if missing:
        print("Missing dog animations:", *(str(x) for x in missing), sep="\n  ", file=sys.stderr)
        print(f"Run: bash download_assets.sh {cfg['color']}", file=sys.stderr)
        return 2
    if args.check:
        print("Configuration and sprite files found. Ready to try the Qt overlay.")
        return 0

    try:
        from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
        from PyQt5.QtGui import QMovie, QPainter, QTransform, QColor, QPen, QPixmap, QCursor
        from PyQt5.QtWidgets import QApplication, QWidget, QMenu
    except ImportError as exc:
        print("PyQt5 is required. On Xubuntu: sudo apt install python3-pyqt5", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 2

    def draw_bone(p, x, y):
        p.save()
        p.translate(round(x), round(y))
        p.setPen(QPen(QColor("#9a8868"), 1))
        p.setBrush(QColor("#f5e6be"))
        p.drawRect(4, 3, 9, 4)
        for bx, by in [(0, 0), (0, 4), (12, 0), (12, 4)]:
            p.drawEllipse(bx, by, 5, 5)
        p.fillRect(4, 4, 10, 3, QColor("#f5e6be"))
        p.restore()

    class Bone(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowFlags(Qt.X11BypassWindowManagerHint | Qt.Tool |
                                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                                Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.resize(18, 10)
            self.setWindowTitle("Panel Pup Bone")

        def paintEvent(self, event):
            p = QPainter(self)
            draw_bone(p, 0, 0)
            p.end()

    class TugOverlay(QWidget):
        """One transparent scene: pointer-held bone and bracing dog together."""
        def __init__(self, pet):
            super().__init__()
            self.pet = pet
            self.setWindowFlags(Qt.X11BypassWindowManagerHint | Qt.Tool |
                                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
                                Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.setGeometry(QApplication.primaryScreen().geometry())
            self.setWindowTitle("Panel Pup Tug")

        def paintEvent(self, event):
            pet = self.pet
            if not pet.dragging:
                return
            b = pet.behavior
            pos = pet.drag_target - self.geometry().topLeft()
            now = time.monotonic()
            source = pet.movies["idle"].currentPixmap()
            bounds = pet.sprite_bounds["idle"]
            strength = max(3.0, min(14.0, 3.0 + (getattr(b, "pull_strength", 30) - 18.0) * 11.0 / 24.0))
            tension = strength + 2 * math.sin(now * 17 + b.pull_phase)
            h = round(pet.dog_height * .95)
            w = round(pet.behavior.width + tension * .55)
            p = QPainter(self)
            p.setRenderHint(QPainter.SmoothPixmapTransform, False)
            # Jaw is the pivot: the bone stays in the user's hand while the
            # rump leans back, shakes, and stretches against it.
            p.save()
            p.translate(pos)
            if b.direction < 0:
                p.scale(-1, 1)
            angle = -5 - strength * .35 + 2 * math.sin(now * 20)
            p.rotate(angle)
            p.drawPixmap(QRect(-w + 3, -round(h * .68), w, h), source, bounds)
            # Braced paws step against the pull, instead of floating neutrally.
            p.setPen(QPen(QColor("#704228"), 2))
            paw_y = round(h * .32) - 1
            for fx in [-w + 9, -round(w * .43)]:
                step = round(2 * math.sin(now * 15 + fx))
                p.drawLine(fx, paw_y - 3, fx - 3 - step, paw_y)
            p.restore()
            # Draw once after the dog so this end is visibly held by the cursor.
            draw_bone(p, pos.x() - 9, pos.y() - 5)
            p.fillRect(pos.x() - (6 if b.direction > 0 else -3), pos.y() - 2,
                       3, 3, QColor("#291c13"))
            p.end()

    class Pup(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowFlags(Qt.X11BypassWindowManagerHint | Qt.Tool | Qt.FramelessWindowHint |
                                Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
            self.setMouseTracking(True)
            self.dragging = False
            self.pointer_mask = 0
            self.pointer_position = QPoint()
            self.drag_offset = QPoint()
            self.drag_target = QPoint()
            self.drag_y = 0.0
            self.drag_tilt = 0.0
            self.bone = Bone()
            self.tug_overlay = TugOverlay(self)
            self.bone_y = cfg["bar_top"] + cfg["bar_height"] - 6
            self.x11 = ctypes.CDLL(ctypes.util.find_library("X11"))
            self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            self.x11.XOpenDisplay.restype = ctypes.c_void_p
            self.x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
            self.x11.XDefaultRootWindow.restype = ctypes.c_ulong
            self.x11.XQueryPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_uint)]
            self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
            self.pointer_display = self.x11.XOpenDisplay(None)
            if not self.pointer_display:
                raise RuntimeError("Cannot open X11 for bone placement")
            self.pointer_root = self.x11.XDefaultRootWindow(self.pointer_display)
            self.right_down = False
            self.movies = {}
            self.sprite_bounds = {}
            for state, path in paths.items():
                m = QMovie(str(path))
                m.setCacheMode(QMovie.CacheAll)
                if not m.isValid():
                    raise RuntimeError(f"Invalid GIF: {path}")
                m.frameChanged.connect(lambda _frame: self.update())
                self.movies[state] = m
                if state in {"idle", "walk", "run"}:
                    bounds = QRect()
                    for index in range(m.frameCount()):
                        m.jumpToFrame(index)
                        image = m.currentImage()
                        for y in range(image.height()):
                            for x in range(image.width()):
                                if image.pixelColor(x, y).alpha():
                                    bounds = bounds.united(QRect(x, y, 1, 1))
                    self.sprite_bounds[state] = bounds
                    m.jumpToFrame(0)
            probe = self.movies["walk"]
            probe.jumpToFrame(0)
            first = probe.currentPixmap()
            if first.isNull():
                raise RuntimeError("Unable to read walking frames")
            self.source_width, self.source_height = first.width(), first.height()
            # Keep the full original GIF image, preserve aspect ratio at display time.
            self.dog_height = cfg["pet_height"]
            self.dog_width = max(1, round(self.source_width * self.dog_height / self.source_height))
            self.resize(self.dog_width, self.dog_height)
            self.floor_y = cfg["bar_top"] + cfg["bar_height"] - self.dog_height
            self.behavior = PetBehavior(cfg["left"], cfg["right"], self.dog_width,
                                        cfg["speed"], cfg["sleep_after"],
                                        basket_enabled="basket_enter" in paths)
            self.behavior.state_until = time.monotonic() + 5.0
            self.behavior.last_touch = time.monotonic()
            self.active_animation = None
            self.hop_started = None
            self.last_time = time.monotonic()
            self.select_animation("walk")
            self.tick_timer = QTimer(self)
            self.tick_timer.setInterval(33)
            self.tick_timer.timeout.connect(self.tick)
            self.tick_timer.start()
            self.move(round(self.behavior.x), self.floor_y)
            self.show()
            self.raise_()
            print(f"Panel Pup started: x={cfg['left']}..{cfg['right']}, "
                  f"y={cfg['bar_top']}..{cfg['bar_top']+cfg['bar_height']}, "
                  f"dog={self.dog_width}x{self.dog_height} px")
            print("Left click: react | Double-click: hop | Right-click panel area: fetch bone | Shift+right-click dog: menu | Ctrl+C: quit")

        def select_animation(self, state):
            filename_state = {"walk": "walk", "run": "run", "idle": "idle",
                              "return": "run", "sleep": "sleep", "react": "react", "hop": "react",
                              "basket_enter": "basket_enter", "basket_rest": "basket_rest",
                              "basket_exit": "basket_exit"}.get(state, "idle")
            if filename_state == self.active_animation:
                return
            if self.active_animation is not None:
                self.movies[self.active_animation].stop()
            self.active_animation = filename_state
            movie = self.movies[filename_state]
            movie.jumpToFrame(0)
            if filename_state.startswith("basket_"):
                frame = movie.currentPixmap()
                # Basket GIFs have a taller canvas with empty space above/below.
                # Display their 95px action area at the normal dog height.
                width = max(1, round(frame.width() * self.dog_height / 95))
            elif filename_state in self.sprite_bounds:
                bounds = self.sprite_bounds[filename_state]
                visible_height = round(self.dog_height * 90 / 95)
                width = max(1, round(bounds.width() * visible_height / bounds.height()))
            else:
                width = self.dog_width
            self.resize(width, self.dog_height)
            self.behavior.width = width
            lo, hi = (self.behavior.fetch_bounds if self.behavior.bone_x is not None or self.behavior.state == "return"
                      else (self.behavior.left, self.behavior.right))
            if self.behavior.carry_until is not None:
                self.behavior.x = self.behavior.bone_x - (width - 9 if self.behavior.direction > 0 else 9)
            self.behavior.x = max(lo, min(self.behavior.x, hi - width))
            movie.start()
            self.update()

        def tick(self):
            now = time.monotonic()
            dt = now - self.last_time
            self.last_time = now
            fullscreen_marker = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'linux-panel-fullscreen'
            if fullscreen_marker.exists():
                if self.isVisible():
                    self.hide()
                    self.bone.hide()
                    self.tug_overlay.hide()
                    if self.dragging: self.finish_tug(now)
                self._fullscreen_hidden = True
                return
            if getattr(self, '_fullscreen_hidden', False):
                self._fullscreen_hidden = False
                self.show()
                self.raise_()
            self.check_bone_click(now)
            if self.dragging and not (self.pointer_mask & (1 << 8)):
                self.finish_tug(now)
            if self.dragging:
                self.resist_pointer(dt, now)
                self.behavior.tug_to(self.drag_target.x() - (self.behavior.width - 9 if self.behavior.direction > 0 else 9), dt, now)
                target_y = max(cfg["bar_top"], min(self.drag_target.y() - self.drag_offset.y(), self.floor_y + 100))
                factor = 1 - math.exp(-min(dt, .1) * 16)
                self.drag_y += (target_y - self.floor_y - self.drag_y) * factor
                stretch = self.drag_target.x() - self.drag_offset.x() - self.behavior.x
                self.drag_tilt = 0
                self.tug_overlay.update()
            else:
                self.drag_y *= math.exp(-min(dt, .1) * 14)
                self.drag_tilt *= math.exp(-min(dt, .1) * 14)
            self.behavior.tick(dt, now)
            state = self.behavior.state
            self.select_animation(state)
            dy = 0
            if state == "hop" and self.hop_started is not None:
                phase = min(1.0, max(0.0, (now - self.hop_started) / 0.62))
                dy = -round(13 * math.sin(math.pi * phase))
            self.move(round(self.behavior.x), self.floor_y + dy + round(self.drag_y))
            self.update_bone()
            self.update()

        def check_bone_click(self, now):
            root, child = ctypes.c_ulong(), ctypes.c_ulong()
            x, y, wx, wy = (ctypes.c_int() for _ in range(4))
            mask = ctypes.c_uint()
            ok = self.x11.XQueryPointer(self.pointer_display, self.pointer_root,
                ctypes.byref(root), ctypes.byref(child), ctypes.byref(x), ctypes.byref(y),
                ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(mask))
            if not ok:
                return
            self.pointer_mask = mask.value
            self.pointer_position = QPoint(x.value, y.value)
            pressed = bool(mask.value & (1 << 10))
            if pressed and not self.right_down and not (mask.value & 1):
                if (QApplication.primaryScreen().geometry().left() <= x.value <= QApplication.primaryScreen().geometry().right() and
                    cfg["bar_top"] <= y.value < cfg["bar_top"] + cfg["bar_height"]):
                    self.place_bone(x.value, y.value, now)
                    self.select_animation("run")
            self.right_down = pressed

        def resist_pointer(self, dt, now):
            # Compare real cursor position with the last point we emitted, so
            # generated mouse moves cannot feed back into the resistance.
            raw = self.pointer_position
            delta = raw - self.pointer_anchor
            if abs(delta.x()) >= 1:
                self.input_x += delta.x()
                self.behavior.face_tug_pointer(self.input_x)
            dx, dy = self.pointer_force.step(delta.x(), delta.y(), dt, now)
            self.pointer_float_x += dx
            self.pointer_float_y += dy
            screen = QApplication.primaryScreen().geometry()
            self.pointer_float_x = max(screen.left(), min(self.pointer_float_x, screen.right()))
            self.pointer_float_y = max(screen.top(), min(self.pointer_float_y, screen.bottom()))
            point = QPoint(round(self.pointer_float_x), round(self.pointer_float_y))
            if point != raw:
                QCursor.setPos(point)
            self.pointer_anchor = point
            self.drag_target = point

        def finish_tug(self, now):
            self.dragging = False
            self.tug_overlay.hide()
            self.setWindowOpacity(1.0)
            self.behavior.end_tug(now)
            self.unsetCursor()

        def place_bone(self, x, y, now):
            self.dragging = False
            self.tug_overlay.hide()
            self.setWindowOpacity(1.0)
            screen = QApplication.primaryScreen().geometry()
            self.bone_y = max(cfg["bar_top"] + 5, min(y, cfg["bar_top"] + cfg["bar_height"] - 5))
            self.behavior.fetch(x, now, (screen.left(), screen.right() + 1))

        def update_bone(self):
            b = self.behavior
            if b.bone_x is None or b.carry_until is not None:
                self.bone.hide()
                return
            self.bone.move(round(b.bone_x - 9), round(self.bone_y - 5))
            self.bone.show()
            self.bone.raise_()

        def closeEvent(self, event):
            self.tug_overlay.close()
            self.bone.close()
            if self.pointer_display:
                self.x11.XCloseDisplay(self.pointer_display)
                self.pointer_display = None
            super().closeEvent(event)

        def paintEvent(self, event):
            pix = self.movies[self.active_animation].currentPixmap()
            if pix.isNull():
                return
            # Build one combined sprite once pickup starts, rather than moving
            # a separate bone window alongside the dog.
            combined = QPixmap(self.size())
            combined.fill(Qt.transparent)
            painter = QPainter(combined)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            # Original sprites appear facing right in typical packs; configurable.
            face_right = self.behavior.direction > 0
            flip = (face_right and cfg["sprite_faces"] == "left") or (
                not face_right and cfg["sprite_faces"] == "right")
            if flip:
                painter.translate(self.width(), 0)
                painter.scale(-1, 1)
            grabbing = self.behavior.state == "grab"
            progress = 1.0
            if grabbing:
                progress = max(0.0, min(1.0, (time.monotonic() - (self.behavior.carry_until - 3.0)) / .5))
                painter.translate(0, round(3 * math.sin(progress * math.pi)))
            target = QRect(0, 0, self.width(), self.height())
            if self.active_animation.startswith("basket_"):
                painter.drawPixmap(target, pix, QRect(0, 40, pix.width(), 95))
            elif self.active_animation in self.sprite_bounds:
                visible_height = round(self.dog_height * 90 / 95)
                target = QRect(0, self.height() - visible_height, self.width(), visible_height)
                painter.drawPixmap(target, pix, self.sprite_bounds[self.active_animation])
            else:
                painter.drawPixmap(target, pix)
            if self.behavior.carry_until is not None:
                # Same source-facing coordinate system as the dog: both mirror
                # together. The pickup lifts the bone from its clicked position.
                bx = self.width() - 18 if cfg["sprite_faces"] == "right" else 0
                start_y = self.bone_y - self.floor_y - 5
                mouth_y = round(self.dog_height * .67)
                by = start_y + (mouth_y - start_y) * progress
                draw_bone(painter, bx, by)
                # A dark muzzle pixel over the middle makes the bone read as
                # gripped between the jaws rather than pasted over the face.
                painter.fillRect(bx + 6, round(by) + 2, 4, 2, QColor("#291c13"))
            painter.end()
            screen_painter = QPainter(self)
            if abs(self.drag_tilt) > .1:
                screen_painter.translate(self.width()/2, self.height()/2)
                screen_painter.rotate(self.drag_tilt)
                screen_painter.translate(-self.width()/2, -self.height()/2)
            screen_painter.drawPixmap(0, 0, combined)
            screen_painter.end()

        def do(self, action):
            now = time.monotonic()
            self.behavior.set_action(action, now)
            if action == "hop":
                self.hop_started = now
            self.select_animation(self.behavior.state)

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton and self.behavior.begin_tug(time.monotonic(), event.globalPos().x()):
                self.dragging = True
                self.drag_offset = event.pos()
                self.drag_target = event.globalPos()
                self.pointer_anchor = QCursor.pos()
                self.pointer_float_x = float(self.pointer_anchor.x())
                self.pointer_float_y = float(self.pointer_anchor.y())
                self.input_x = float(event.globalPos().x())
                self.pointer_force = PointerResistance(time.monotonic(), self.behavior.direction)
                self.setWindowOpacity(0.0)
                self.tug_overlay.show()
                self.tug_overlay.raise_()
                self.tug_overlay.update()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            if self.dragging:
                # Tick samples physical deltas; ignore warp-generated events.
                event.accept()
                return
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):
            if event.button() == Qt.LeftButton and self.dragging:
                self.finish_tug(time.monotonic())
                event.accept()
                return
            if event.button() == Qt.LeftButton:
                self.do("leave_basket" if self.behavior.state.startswith("basket_")
                        else cfg["on_click"])
            elif event.button() == Qt.MiddleButton:
                self.do(cfg["on_middle_click"])
            event.accept()

        def mouseDoubleClickEvent(self, event):
            if event.button() == Qt.LeftButton and self.behavior.carry_until is not None:
                self.mousePressEvent(event)
            elif event.button() == Qt.LeftButton:
                self.do(cfg["on_double_click"])
                event.accept()
            else:
                super().mouseDoubleClickEvent(event)

        def contextMenuEvent(self, event):
            if not (event.modifiers() & Qt.ShiftModifier):
                self.place_bone(event.globalPos().x(), event.globalPos().y(), time.monotonic())
                self.select_animation("run")
                event.accept()
                return
            menu = QMenu(self)
            menu.addAction("Pet / Happy", lambda: self.do("react"))
            menu.addAction("Walk", lambda: self.do("walk"))
            menu.addAction("Run", lambda: self.do("run"))
            menu.addAction("Rest in basket" if "basket_enter" in paths else "Take a nap", lambda: self.do("nap"))
            menu.addAction("Little hop", lambda: self.do("hop"))
            if self.behavior.paused:
                menu.addAction("Resume", lambda: self.do("resume"))
            else:
                menu.addAction("Pause", lambda: self.do("pause"))
            menu.addSeparator()
            menu.addAction("Quit Panel Pup", self.close)
            menu.exec_(event.globalPos())

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(True)
    pet = Pup()
    return app.exec_()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as e:
        print(f"Panel Pup error: {e}", file=sys.stderr)
        sys.exit(2)
