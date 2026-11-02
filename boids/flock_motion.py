"""Smooth heading-based flock movement near screen edges, independent of Qt."""
import math

def clamp(value,low,high):return max(low,min(high,value))
def angle_delta(target,current):return math.atan2(math.sin(target-current),math.cos(target-current))

def move_bird(x,y,vx,vy,wanted_x,wanted_y,bounds,dt,cruise_speed,turn_bias=1):
    left,top,right,bottom=bounds
    speed=clamp(math.hypot(wanted_x,wanted_y),cruise_speed*.7,cruise_speed*1.4)
    heading=math.atan2(vy,vx) if vx or vy else math.atan2(wanted_y,wanted_x)
    wanted=math.atan2(wanted_y,wanted_x) if wanted_x or wanted_y else heading
    # Keep the turning circle small at higher speeds, without reversing velocity.
    turn_rate=max(2.0,speed/32)
    radius=speed/turn_rate
    zone=min(2*radius+20,(right-left)/4,(bottom-top)/4)
    ux,uy=math.cos(heading),math.sin(heading)
    normal_x=normal_y=strength=0.
    for distance,nx,ny in ((x-left,1,0),(right-x,-1,0),(y-top,0,1),(bottom-y,0,-1)):
        if distance>=zone:continue
        inward=ux*nx+uy*ny
        proximity=clamp((zone-distance)/max(1,zone-radius-6),0,1)
        risk=proximity*clamp((.7-inward)/.7,0,1)
        normal_x+=nx*risk;normal_y+=ny*risk;strength=max(strength,risk)
    flock_rate=clamp(angle_delta(wanted,heading)/dt,-turn_rate,turn_rate)
    if normal_x or normal_y:
        difference=angle_delta(math.atan2(normal_y,normal_x),heading)
        # A perfectly head-on approach still needs a sideways turn. Alternate
        # the tie-break direction rather than braking in place at the wall.
        if abs(difference)>math.pi-.02:difference=math.copysign(abs(difference),turn_bias)
        wall_rate=clamp(difference/dt,-turn_rate,turn_rate)
        angular_rate=wall_rate*strength+flock_rate*(1-strength)
    else:angular_rate=flock_rate
    heading+=angular_rate*dt
    vx,vy=speed*math.cos(heading),speed*math.sin(heading)
    new_x,new_y=x+vx*dt,y+vy*dt
    # Emergency envelope only: normal approaches should turn before reaching it.
    if new_x<left:new_x=left;vx=max(0,vx)
    if new_x>right:new_x=right;vx=min(0,vx)
    if new_y<top:new_y=top;vy=max(0,vy)
    if new_y>bottom:new_y=bottom;vy=min(0,vy)
    return new_x,new_y,vx,vy
