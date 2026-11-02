import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flock_motion import move_bird,angle_delta

BOUNDS=(10,48,1909,1069)
class EdgeSteeringTests(unittest.TestCase):
    def test_head_on_and_corner_approaches_turn_without_hitting_or_stopping(self):
        approaches=((1800,500,0),(100,500,math.pi),(900,150,-math.pi/2),(900,950,math.pi/2),(1800,950,math.pi/4))
        for speed in (15,48,100,120):
            for dt in (1/24,1/10):
                for x,y,heading in approaches:
                    with self.subTest(speed=speed,dt=dt,heading=heading):
                        bird=(x,y,speed*math.cos(heading),speed*math.sin(heading))
                        for _ in range(int(30/dt)):
                            old=bird
                            bird=move_bird(*bird,bird[2],bird[3],BOUNDS,dt,speed)
                            self.assertTrue(10<bird[0]<1909 and 48<bird[1]<1069)
                            self.assertAlmostEqual(math.hypot(bird[2],bird[3]),speed,places=5)
                            change=abs(angle_delta(math.atan2(bird[3],bird[2]),math.atan2(old[3],old[2])))
                            self.assertLessEqual(change,max(2,speed/32)*dt+1e-8)
    def test_head_on_tie_break_can_turn_either_way(self):
        left=move_bird(1870,500,100,0,100,0,BOUNDS,1/24,100,1)
        right=move_bird(1870,500,100,0,100,0,BOUNDS,1/24,100,-1)
        self.assertGreater(left[3],0);self.assertLess(right[3],0)
        self.assertAlmostEqual(left[0],right[0])
    def test_safety_envelope_handles_a_resize_outside_the_flight_area(self):
        bird=move_bird(-20,20,-80,-80,-80,-80,BOUNDS,.1,100)
        self.assertTrue(10<=bird[0]<=1909 and 48<=bird[1]<=1069)
        self.assertGreaterEqual(bird[2],0);self.assertGreaterEqual(bird[3],0)
if __name__=='__main__':unittest.main()
