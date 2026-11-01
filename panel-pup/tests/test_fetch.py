import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from behavior import PetBehavior

class FetchTests(unittest.TestCase):
    def test_reaches_bone_from_either_side(self):
        for start,target,direction in [(0,180,1),(160,10,-1)]:
            b=PetBehavior(0,200,40);b.x=start;b.fetch(target,0)
            self.assertEqual(b.direction,direction)
            for i in range(100):
                b.tick(.05,i*.05)
                self.assertTrue(0<=b.x<=160)
                if b.carry_until is not None:break
            self.assertIsNotNone(b.carry_until)
            self.assertEqual(b.state,'grab')
            b.tick(.05,b.carry_until)
            self.assertIsNone(b.bone_x)
    def test_fetch_outside_roaming_area_and_return(self):
        b=PetBehavior(600,1000,40);b.fetch(1400,0,(0,1920))
        for i in range(400):
            b.tick(.05,i*.05)
            if b.carry_until is not None:break
        self.assertIsNotNone(b.carry_until)
        self.assertGreater(b.x,1000)
        start=b.carry_until
        b.tick(.05,start)
        self.assertEqual(b.state,'return')
        previous=b.x
        b.tick(.05,start+.05)
        self.assertLess(b.x,previous)
        self.assertGreater(b.x,1000)  # walks back rather than teleporting
        for i in range(200):b.tick(.05,start+.1+i*.05)
        self.assertTrue(600<=b.x<=960)

    def test_new_bone_replaces_old_and_wakes_pet(self):
        b=PetBehavior(0,200,40,basket_enabled=True);b.set_action('nap',0)
        b.fetch(180,1);b.fetch(20,2)
        self.assertEqual(b.bone_x,20);self.assertEqual(b.state,'run')
        b.set_action('pause',3);self.assertIsNone(b.bone_x)
    def test_edge_bones_do_not_move_dog_outside_area(self):
        for target in [-100,500]:
            b=PetBehavior(0,200,40);b.fetch(target,0)
            self.assertTrue(8<=b.bone_x<=192)
            for i in range(100):
                b.tick(.05,i*.05);self.assertTrue(0<=b.x<=160)
