import sys,unittest,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from behavior import PointerResistance

class PointerTests(unittest.TestCase):
    def test_normal_drag_is_slowed(self):
        p=PointerResistance(0,rng=random.Random(1))
        x,y=p.step(10,0,.033,.1)
        self.assertTrue(0<x<5);self.assertEqual(y,0)
    def test_hard_pull_can_reverse_physical_movement(self):
        p=PointerResistance(0,rng=random.Random(1))
        x,y=p.step(2,0,.033,p.next_switch+.01)
        self.assertTrue(p.hard);self.assertLess(x,0)
        x,y=p.step(-2,0,.033,p.next_switch-.01)
        self.assertGreater(x,0)
    def test_warp_feedback_cannot_accelerate_pull(self):
        p=PointerResistance(0,rng=random.Random(1))
        p.step(2,0,.033,p.next_switch+.01)
        x,y=p.step(0,0,.033,p.next_switch-.01)
        self.assertLess(x,0);self.assertLess(abs(x),6)
    def test_long_frame_and_big_input_are_bounded(self):
        p=PointerResistance(0,rng=random.Random(1))
        x,y=p.step(9999,-9999,10,.1)
        self.assertLessEqual(abs(x),35);self.assertLessEqual(abs(y),35)
