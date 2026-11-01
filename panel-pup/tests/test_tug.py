import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from behavior import PetBehavior

class TugTests(unittest.TestCase):
    def holding(self):
        b=PetBehavior(0,200,40);b.fetch(80,0,(0,400))
        for i in range(100):
            b.tick(.05,i*.05)
            if b.carry_until is not None:return b
        self.fail('Did not pick up bone')
    def test_requires_picked_up_bone(self):
        b=PetBehavior(0,200,40)
        self.assertFalse(b.begin_tug(1))
        b.fetch(180,2)
        self.assertFalse(b.begin_tug(2))
    def test_long_drag_retains_bone_and_release_restarts_hold(self):
        b=self.holding();self.assertTrue(b.begin_tug(10))
        before=b.x
        b.tug_to(300,.05,30);b.tick(.05,30)
        self.assertGreater(b.x,before);self.assertLess(b.x,300)
        self.assertEqual(b.state,'tug');self.assertIsNotNone(b.bone_x)
        b.end_tug(30);self.assertEqual(b.state,'hold')
        b.tick(.05,31);self.assertIsNotNone(b.bone_x)
        b.tick(.05,33);self.assertIsNone(b.bone_x)
    def test_drag_clamps_and_new_bone_cancels_drag(self):
        b=self.holding();b.begin_tug(1)
        for i in range(100):b.tug_to(900,.1,2+i)
        self.assertLessEqual(b.x,360)
        b.fetch(20,200);self.assertFalse(b.tugging)

    def test_pull_varies_but_stays_bounded(self):
        b=self.holding();b.rng.seed(42);b.begin_tug(1)
        strengths=set()
        for i in range(200):
            now=1+i*.05
            b.tug_to(200,.05,now)
            strengths.add(round(b.pull_strength,2))
            self.assertTrue(18<=b.pull_strength<=42)
            self.assertTrue(0<=b.x<=360)
        self.assertGreater(len(strengths),5)
        self.assertTrue(b.tugging)

    def test_follows_drag_direction_and_ignores_jitter(self):
        b=self.holding();b.begin_tug(1,100)
        b.face_tug_pointer(120)
        self.assertEqual(b.direction,1)  # body is left of cursor, facing right
        b.face_tug_pointer(118)
        self.assertEqual(b.direction,1)
        b.face_tug_pointer(116)
        self.assertEqual(b.direction,-1)  # body is right of cursor, facing left
        b.face_tug_pointer(100)
        self.assertEqual(b.direction,-1)
        b.face_tug_pointer(110)
        self.assertEqual(b.direction,1)

    def test_strong_tug_holds_back_after_sustained_pull(self):
        b=self.holding();b.rng.seed(5);b.begin_tug(1)
        for i in range(100):b.tug_to(200,.05,1+i*.05)
        self.assertLess(b.x,185)  # visible sustained resistance, not just initial lag
        self.assertGreater(b.x,130)
