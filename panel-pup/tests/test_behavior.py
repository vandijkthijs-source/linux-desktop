import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from behavior import PetBehavior


class TestWalking(unittest.TestCase):
    def test_no_escape_right_edge(self):
        b = PetBehavior(200, 350, 40, speed=500)
        for i in range(300):
            b.tick(0.033, i / 30)
            self.assertGreaterEqual(b.x, 200)
            self.assertLessEqual(b.x, 310)

    def test_no_escape_left_edge(self):
        b = PetBehavior(200, 350, 40, speed=500)
        b.x = 200
        b.direction = -1
        b.tick(0.1, 1)
        self.assertEqual(b.x, 200)
        self.assertEqual(b.direction, 1)

    def test_pet_reacts_then_idles(self):
        b = PetBehavior(0, 150, 40)
        b.set_action('react', 10)
        self.assertEqual(b.state, 'react')
        b.tick(0.03, 11.21)
        self.assertEqual(b.state, 'idle')

    def test_pause_stops_motion(self):
        b = PetBehavior(0, 150, 40)
        b.set_action('pause', 1)
        b.tick(.05, 3)
        self.assertEqual(b.x, 0)
        self.assertTrue(b.paused)

    def test_basket_cycle_stays_put_and_returns_to_idle(self):
        b = PetBehavior(0, 150, 40, sleep_after=2, basket_enabled=True)
        b.state_until = 1
        b.tick(.05, 3)
        self.assertEqual(b.state, 'basket_enter')
        x = b.x
        b.tick(.05, b.state_until)
        self.assertEqual(b.state, 'basket_rest')
        b.tick(.05, b.state_until)
        self.assertEqual(b.state, 'basket_exit')
        b.tick(.05, b.state_until)
        self.assertEqual(b.state, 'idle')
        self.assertEqual(b.x, x)
        self.assertEqual(b.last_touch, b.state_until - 2)

    def test_basket_nap_can_be_interrupted(self):
        b = PetBehavior(0, 150, 40, basket_enabled=True)
        b.set_action('nap', 10)
        self.assertEqual(b.state, 'basket_enter')
        b.set_action('walk', 11)
        self.assertEqual(b.state, 'walk')

    def test_click_leaves_basket_without_restarting_exit(self):
        b = PetBehavior(0, 150, 40, basket_enabled=True)
        for state in ('basket_enter', 'basket_rest'):
            b.state = state
            b.set_action('leave_basket', 10)
            self.assertEqual(b.state, 'basket_exit')
            deadline = b.state_until
            b.set_action('leave_basket', 11)
            self.assertEqual(b.state_until, deadline)
            b.tick(.03, deadline)
            self.assertEqual(b.state, 'idle')
        b.set_action('run', 20)
        self.assertEqual(b.state, 'run')

    def test_small_space_error(self):
        with self.assertRaises(ValueError):
            PetBehavior(0, 30, 40)

    def test_sleep_after_idle(self):
        b = PetBehavior(0, 150, 40, sleep_after=2)
        b.state = 'idle'
        b.state_until = 1
        b.tick(.05, 3)
        self.assertEqual(b.state, 'sleep')


if __name__ == '__main__':
    unittest.main()
