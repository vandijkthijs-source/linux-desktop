"""Pure Python movement + interaction state, independently testable without Qt."""
from __future__ import annotations
from dataclasses import dataclass
import random


@dataclass
class PetBehavior:
    left: float
    right: float
    width: float
    speed: float = 38.0
    sleep_after: float = 80.0
    basket_enabled: bool = False
    basket_enter_duration: float = 1.57
    basket_exit_duration: float = 1.86

    def __post_init__(self):
        if self.right - self.left < self.width:
            raise ValueError("Walking area must be wider than the dog sprite")
        self.x = float(self.left)
        self.direction = 1
        self.state = "walk"
        self.state_until = 5.0
        self.last_touch = 0.0
        self.paused = False
        self.rng = random.Random()
        self.tugging = False
        self.bone_x = None
        self.carry_until = None

    def set_action(self, action: str, now: float) -> None:
        """Actions exposed to mouse controls. No desktop side effects."""
        self.tugging = False
        self.bone_x = None
        self.carry_until = None
        if action == "pause":
            self.paused = True
            self.state = "idle"
            return
        if action == "resume":
            self.paused = False
            self.state = "walk"
            self.state_until = now + 4.0
            self.last_touch = now
            return
        self.paused = False
        self.last_touch = now
        if action == "leave_basket":
            if self.state in {"basket_enter", "basket_rest"}:
                self.state, self.state_until = "basket_exit", now + self.basket_exit_duration
        elif action == "react":
            self.state, self.state_until = "react", now + 1.2
        elif action == "hop":
            self.state, self.state_until = "hop", now + 0.62
        elif action == "nap":
            self.state = "basket_enter" if self.basket_enabled else "sleep"
            self.state_until = now + (self.basket_enter_duration if self.basket_enabled else 10.0)
        elif action == "walk":
            self.state, self.state_until = "walk", now + 8.0
        elif action == "run":
            self.state, self.state_until = "run", now + 2.0
        else:
            raise ValueError(f"Unknown pet action: {action}")

    def fetch(self, x: float, now: float, bounds=None) -> None:
        self.tugging = False
        self.paused = False
        self.fetch_bounds = bounds or (self.left, self.right)
        lo, hi = self.fetch_bounds
        self.bone_x = max(lo + 9, min(float(x), hi - 9))
        self.carry_until = None
        self.last_touch = now
        self.direction = 1 if self.bone_x >= self.x + self.width / 2 else -1
        self.state = "run"

    def begin_tug(self, now, cursor_x=None):
        if self.bone_x is None or self.carry_until is None:
            return False
        self.tugging = True
        self.tug_cursor_x = cursor_x
        self.pull_strength = self.rng.uniform(24, 36)
        self.next_pull = now + self.rng.uniform(.12, .35)
        self.pull_phase = self.rng.uniform(0, 6.28)
        self.state = "tug"
        self.last_touch = now
        return True

    def face_tug_pointer(self, cursor_x):
        if not self.tugging:
            return
        if self.tug_cursor_x is None:
            self.tug_cursor_x = cursor_x
            return
        delta = cursor_x - self.tug_cursor_x
        # Ignore tiny jitter but accumulate deliberate movement in either direction.
        if abs(delta) >= 3:
            self.direction = 1 if delta > 0 else -1
            self.tug_cursor_x = cursor_x

    def tug_to(self, x, dt, now):
        if not self.tugging:
            return
        import math
        lo, hi = self.fetch_bounds
        if now >= self.next_pull:
            self.pull_strength = self.rng.uniform(18, 42)
            self.next_pull = now + self.rng.uniform(.12, .45)
        target = max(lo, min(float(x), hi - self.width))
        resistance = self.pull_strength * (.85 + .35 * math.sin(now * 15 + self.pull_phase))
        resisted = max(lo, min(target - self.direction * resistance, hi - self.width))
        stiffness = 3.0 + (42 - self.pull_strength) * .12
        self.x += (resisted - self.x) * (1 - math.exp(-max(0, min(dt, .1)) * stiffness))
        self.bone_x = self.x + (self.width - 9 if self.direction > 0 else 9)
        self.last_touch = now

    def end_tug(self, now):
        if not self.tugging:
            return
        self.tugging = False
        self.state = "hold"
        self.carry_until = now + 2.5
        self.last_touch = now

    def tick(self, dt: float, now: float) -> None:
        """Advance in seconds; clamp pet to left/right limits at every tick."""
        if self.paused or self.tugging:
            return
        dt = max(0.0, min(dt, 0.1))
        if self.bone_x is not None:
            if self.carry_until is not None:
                if now >= self.carry_until - 2.5:
                    self.state = "hold"
                if now >= self.carry_until:
                    self.bone_x = None
                    self.carry_until = None
                    self.state, self.state_until = ("return" if self.x < self.left or self.x > self.right - self.width else "idle"), now + 2.0
                return
            # Place the mouth at the bone; clamp at the existing walking limits.
            target = self.bone_x - (self.width - 9 if self.direction > 0 else 9)
            lo, hi = self.fetch_bounds
            target = max(lo, min(target, hi - self.width))
            distance = target - self.x
            step = self.speed * 5.0 * dt
            if abs(distance) <= step:
                self.x = target
                self.state = "grab"
                self.carry_until = now + 3.0
            else:
                self.x += step if distance > 0 else -step
                self.state = "run"
            return
        if self.state == "return":
            target = max(self.left, min(self.x, self.right - self.width))
            distance = target - self.x
            self.direction = 1 if distance > 0 else -1
            step = self.speed * 3 * dt
            if abs(distance) <= step:
                self.x = target
                self.state, self.state_until = "idle", now + 2
            else:
                self.x += step if distance > 0 else -step
            return
        if now >= self.state_until:
            if self.state == "basket_enter":
                self.state, self.state_until = "basket_rest", now + self.rng.uniform(15, 30)
            elif self.state == "basket_rest":
                self.state, self.state_until = "basket_exit", now + self.basket_exit_duration
            elif self.state == "basket_exit":
                self.state, self.state_until = "idle", now + 2.0
                self.last_touch = now
            elif self.state in {"react", "hop", "sleep", "run"}:
                self.state, self.state_until = "idle", now + 2.0
            elif now - self.last_touch >= self.sleep_after and self.state != "sleep":
                self.state = "basket_enter" if self.basket_enabled else "sleep"
                self.state_until = now + (self.basket_enter_duration if self.basket_enabled
                                          else self.rng.uniform(6, 12))
                self.last_touch = now   # avoid sleeping continuously
            elif self.state == "walk":
                self.state, self.state_until = "idle", now + self.rng.uniform(2.0, 4.0)
            else:
                self.state, self.state_until = "walk", now + self.rng.uniform(4.0, 7.0)
                if self.rng.random() < 0.4:
                    self.direction *= -1
        if self.state in {"walk", "run"}:
            velocity = self.speed * (1.7 if self.state == "run" else 1)
            self.x += self.direction * velocity * dt
            max_x = self.right - self.width
            if self.x >= max_x:
                self.x = max_x
                self.direction = -1
            elif self.x <= self.left:
                self.x = self.left
                self.direction = 1


class PointerResistance:
    """Map physical deltas to resisted deltas, active only during a held tug."""
    def __init__(self, now, direction=1, rng=None):
        self.rng = rng or random.Random()
        self.hard = False
        self.next_switch = now + self.rng.uniform(.4, .8)
        self.gain = self.rng.uniform(.22, .4)
        self.force = 0.0
        self.last_direction = (float(direction), 0.0)

    def step(self, dx, dy, dt, now):
        import math
        dt = max(0.0, min(dt, .05))
        length = math.hypot(dx, dy)
        if length >= 1:
            self.last_direction = (dx / length, dy / length)
        if now >= self.next_switch:
            self.hard = not self.hard
            self.next_switch = now + self.rng.uniform(.18, .38) if self.hard else now + self.rng.uniform(.45, 1.0)
            self.gain = self.rng.uniform(.04, .15) if self.hard else self.rng.uniform(.22, .4)
            self.force = self.rng.uniform(100, 165) if self.hard else 0.0
        ux, uy = self.last_direction
        # A hard pull can overpower continued forward movement. Deltas from
        # our own previous pointer warp are excluded by the caller.
        out_x = dx * self.gain - ux * self.force * dt
        out_y = dy * self.gain - uy * self.force * dt
        return max(-35, min(35, out_x)), max(-35, min(35, out_y))
