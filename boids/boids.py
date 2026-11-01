#!/usr/bin/python3
"""Small X11 flock overlay. No wallpaper changes, input capture or network access."""
import ctypes as C
import ctypes.util
import fcntl
import json
import math
import os
from pathlib import Path
import random
import signal
import socket
import sys
import time
from PyQt5.QtCore import Qt, QTimer, QPointF, QRect, QSocketNotifier
from PyQt5.QtGui import QColor, QPainter, QPolygonF, QRegion
from PyQt5.QtWidgets import QApplication, QWidget
from settings import load, save
from controls import Controls

runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp')) / ('desktop-boids-' + str(os.getuid()))
runtime.mkdir(mode=0o700, exist_ok=True)
if '--toggle' in sys.argv:
    cfg=load();cfg['enabled']=not cfg['enabled'];save(cfg)
    sys.exit(0)
lock = open(runtime / 'lock', 'w')
try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError: sys.exit(0)
if os.environ.get('XDG_SESSION_TYPE') != 'x11': sys.exit('Boids requires an X11 session.')
try: os.nice(10)
except OSError: pass

class WindowAttributes(C.Structure):
    _fields_=[('x',C.c_int),('y',C.c_int),('width',C.c_int),('height',C.c_int),('border_width',C.c_int),('depth',C.c_int),('visual',C.c_void_p),('root',C.c_ulong),('window_class',C.c_int),('bit_gravity',C.c_int),('win_gravity',C.c_int),('backing_store',C.c_int),('backing_planes',C.c_ulong),('backing_pixel',C.c_ulong),('save_under',C.c_int),('colormap',C.c_ulong),('map_installed',C.c_int),('map_state',C.c_int),('all_event_masks',C.c_long),('your_event_mask',C.c_long),('do_not_propagate_mask',C.c_long),('override_redirect',C.c_int),('screen',C.c_void_p)]

class WindowChanges(C.Structure):
    _fields_=[('x',C.c_int),('y',C.c_int),('width',C.c_int),('height',C.c_int),('border_width',C.c_int),('sibling',C.c_ulong),('stack_mode',C.c_int)]

class X11:
    def __init__(self):
        self.x = C.CDLL(ctypes.util.find_library('X11'))
        x = self.x
        x.XOpenDisplay.argtypes=[C.c_char_p]; x.XOpenDisplay.restype=C.c_void_p
        x.XDefaultRootWindow.argtypes=[C.c_void_p]; x.XDefaultRootWindow.restype=C.c_ulong
        x.XInternAtom.argtypes=[C.c_void_p,C.c_char_p,C.c_int]; x.XInternAtom.restype=C.c_ulong
        x.XGetWindowProperty.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ubyte))]
        x.XFree.argtypes=[C.c_void_p]
        x.XChangeProperty.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_ulong,C.c_int,C.c_int,C.POINTER(C.c_ubyte),C.c_int]
        x.XGetGeometry.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)]
        x.XTranslateCoordinates.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_int,C.c_int,C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_ulong)]
        x.XConfigureWindow.argtypes=[C.c_void_p,C.c_ulong,C.c_uint,C.POINTER(WindowChanges)]
        x.XFlush.argtypes=[C.c_void_p]
        x.XGetWindowAttributes.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(WindowAttributes)]
        x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
        self.error_type=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)
        self.handler=self.error_type(lambda *_:0)
        x.XSetErrorHandler.argtypes=[self.error_type]; x.XSetErrorHandler(self.handler)
        self.d=x.XOpenDisplay(None)
        if not self.d: raise RuntimeError('No X display')
        self.root=x.XDefaultRootWindow(self.d); self.atoms={}
        self.fixes=C.CDLL(ctypes.util.find_library('Xfixes'))
        self.fixes.XFixesCreateRegion.argtypes=[C.c_void_p,C.c_void_p,C.c_int]
        self.fixes.XFixesCreateRegion.restype=C.c_ulong
        self.fixes.XFixesSetWindowShapeRegion.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_int,C.c_ulong]
        self.empty_input=self.fixes.XFixesCreateRegion(self.d,None,0)
    def atom(self,name):
        if name not in self.atoms: self.atoms[name]=self.x.XInternAtom(self.d,name.encode(),0)
        return self.atoms[name]
    def prop(self,w,name):
        actual=C.c_ulong(); fmt=C.c_int(); count=C.c_ulong(); rest=C.c_ulong(); data=C.POINTER(C.c_ubyte)()
        rc=self.x.XGetWindowProperty(self.d,w,self.atom(name),0,2048,0,0,C.byref(actual),C.byref(fmt),C.byref(count),C.byref(rest),C.byref(data))
        try:
            return list(C.cast(data,C.POINTER(C.c_ulong))[:count.value]) if not rc and fmt.value==32 and data else []
        finally:
            if data: self.x.XFree(data)
    def top_level(self,w):
        for _ in range(12):
            root=C.c_ulong(); parent=C.c_ulong(); children=C.POINTER(C.c_ulong)(); count=C.c_uint()
            ok=self.x.XQueryTree(self.d,w,C.byref(root),C.byref(parent),C.byref(children),C.byref(count))
            if children: self.x.XFree(children)
            if not ok or parent.value==self.root: return w
            w=parent.value
        return w
    def click_through(self,w):
        # Qt empties the client's input shape, but XFWM can add a frame which
        # still receives clicks. Both need an empty ShapeInput region.
        for target in {w,self.top_level(w)}:
            self.fixes.XFixesSetWindowShapeRegion(self.d,target,2,0,0,self.empty_input)
        self.x.XFlush(self.d)
    def rect(self,w):
        root=C.c_ulong(); x=C.c_int(); y=C.c_int(); width=C.c_uint(); height=C.c_uint(); border=C.c_uint(); depth=C.c_uint(); child=C.c_ulong()
        if not self.x.XGetGeometry(self.d,w,C.byref(root),C.byref(x),C.byref(y),C.byref(width),C.byref(height),C.byref(border),C.byref(depth)): return QRect()
        self.x.XTranslateCoordinates(self.d,w,self.root,0,0,C.byref(x),C.byref(y),C.byref(child))
        return QRect(x.value,y.value,width.value,height.value)

class Wallpaper(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.Window|Qt.WindowDoesNotAcceptFocus|Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle('Desktop Boids')
        self.x=X11(); self.covered_since=None; self.paused=False; self.frames=0; self.sim_seconds=0.; self.started=time.monotonic()
        self.cfg=load(); self.boids=[]; self.rng=random.Random(42); rng=self.rng
        geom=QApplication.primaryScreen().virtualGeometry(); self.setGeometry(geom)
        for i in range(self.cfg['count']):
            angle=rng.random()*math.tau
            self.boids.append([rng.random()*geom.width(),rng.random()*geom.height(),math.cos(angle)*48,math.sin(angle)*48])
        bounds=self.flight_rect()
        for b in self.boids:
            b[0]=max(bounds.left(),min(bounds.right(),b[0]));b[1]=max(bounds.top(),min(bounds.bottom(),b[1]))
        # Use XFWM's desktop layer rather than an override-redirect overlay.
        # This also survives Show Desktop and workspace/window transitions.
        xid=int(self.winId());x=self.x
        desktop_type=(C.c_ulong*1)(x.atom('_NET_WM_WINDOW_TYPE_DESKTOP'))
        x.x.XChangeProperty(x.d,xid,x.atom('_NET_WM_WINDOW_TYPE'),4,32,0,C.cast(desktop_type,C.POINTER(C.c_ubyte)),1)
        all_desktops=(C.c_ulong*1)(0xffffffff)
        x.x.XChangeProperty(x.d,xid,x.atom('_NET_WM_DESKTOP'),6,32,0,C.cast(all_desktops,C.POINTER(C.c_ubyte)),1)
        states=(C.c_ulong*4)(x.atom('_NET_WM_STATE_SKIP_TASKBAR'),x.atom('_NET_WM_STATE_SKIP_PAGER'),x.atom('_NET_WM_STATE_STICKY'),x.atom('_NET_WM_STATE_BELOW'))
        x.x.XChangeProperty(x.d,xid,x.atom('_NET_WM_STATE'),4,32,0,C.cast(states,C.POINTER(C.c_ubyte)),4)
        x.x.XFlush(x.d)
        self.last=time.monotonic();self.show()
        QTimer.singleShot(200,lambda:self.setGeometry(geom))
        QTimer.singleShot(250,lambda:self.x.click_through(int(self.winId())))
        QTimer.singleShot(350,self.background_layer)
        self.timer=QTimer(self); self.timer.timeout.connect(self.step)
        self.poller=QTimer(self); self.poller.timeout.connect(self.check); self.poller.start(500)
        QApplication.primaryScreen().virtualGeometryChanged.connect(self.resize_desktop)
        self.settings_timer=QTimer(self);self.settings_timer.timeout.connect(self.refresh_settings);self.settings_timer.start(200)
        self.check()
    def background_layer(self):
        # In XFWM, BELOW is above DESKTOP and below normal apps. Keeping the
        # desktop type also preserves Show Desktop and all-workspace behaviour.
        import subprocess
        subprocess.run(['wmctrl','-i','-r',hex(int(self.winId())),'-b','add,below'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.x.click_through(int(self.winId()))
    def refresh_settings(self):
        cfg=load()
        if cfg==self.cfg:return
        self.cfg=cfg
        self.boids=self.boids[:cfg['count']]
        while len(self.boids)<cfg['count']:
            angle=self.rng.random()*math.tau
            self.boids.append([self.rng.random()*self.width(),self.rng.random()*self.height(),math.cos(angle)*cfg['speed'],math.sin(angle)*cfg['speed']])
        bounds=self.flight_rect()
        for b in self.boids:
            b[0]=max(bounds.left(),min(bounds.right(),b[0]));b[1]=max(bounds.top(),min(bounds.bottom(),b[1]))
        self.check();self.update()
    def flight_rect(self):
        # The top panel is a reserved area, not part of the birds' airspace.
        available=QApplication.primaryScreen().availableGeometry()
        pad=self.cfg['size']+1
        return available.translated(-self.geometry().x(),-self.geometry().y()).adjusted(pad,pad,-pad,-pad)
    def resize_desktop(self,*_):
        self.setGeometry(QApplication.primaryScreen().virtualGeometry())
    def check(self):
        x=self.x; x.click_through(int(self.winId())); clients=x.prop(x.root,'_NET_CLIENT_LIST_STACKING'); desktop=None
        current=(x.prop(x.root,'_NET_CURRENT_DESKTOP') or [0])[0]
        visible=QRegion()
        for screen in QApplication.screens():visible=visible.united(QRegion(screen.availableGeometry()))
        active=(x.prop(x.root,'_NET_ACTIVE_WINDOW') or [0])[0]
        fullscreen=False
        for w in clients:
            types=x.prop(w,'_NET_WM_WINDOW_TYPE')
            if x.atom('_NET_WM_WINDOW_TYPE_DESKTOP') in types:
                desktop=w; continue
            if w==int(self.winId()): continue
            attrs=WindowAttributes()
            if not x.x.XGetWindowAttributes(x.d,w,C.byref(attrs)) or attrs.map_state!=2: continue
            state=x.prop(w,'_NET_WM_STATE')
            if x.atom('_NET_WM_STATE_HIDDEN') in state: continue
            wd=x.prop(w,'_NET_WM_DESKTOP')
            if wd and wd[0] not in (current,0xffffffff): continue
            if w==active and x.atom('_NET_WM_STATE_FULLSCREEN') in state: fullscreen=True
            # Docks/panels remain above the flock, but do not pause it.
            if x.atom('_NET_WM_WINDOW_TYPE_DOCK') not in types: visible=visible.subtracted(QRegion(x.rect(w)))
        battery=False
        for p in Path('/sys/class/power_supply').glob('*/status'):
            try: battery |= p.read_text().strip()=='Discharging'
            except OSError: pass
        exposed=sum(r.width()*r.height() for r in visible.rects())
        # Brief activation/coverage changes are common while tabs and windows
        # open. Pause only after two seconds of sustained complete coverage.
        covered=fullscreen or exposed < 64
        now=time.monotonic()
        if covered:
            if self.covered_since is None:self.covered_since=now
        else:self.covered_since=None
        paused=(self.covered_since is not None and now-self.covered_since>=2) or not self.cfg['enabled'] or (runtime/'paused').exists()
        was_paused=self.paused
        self.paused=paused
        if was_paused and not paused:self.update()
        if self.cfg['enabled']:
            if not self.isVisible():self.show()
        elif self.isVisible():self.hide()
        if paused: self.timer.stop()
        else:
            interval=round(1000/min(self.cfg['fps'],10)) if battery else round(1000/self.cfg['fps'])
            if not self.timer.isActive() or self.timer.interval()!=interval:
                self.last=time.monotonic(); self.timer.start(interval)
        (runtime/'status.json').write_text(json.dumps({'paused':paused,'enabled':self.cfg['enabled'],'covered':covered,'fps_limit':min(self.cfg['fps'],10) if battery else self.cfg['fps'],'boids':len(self.boids),'frames':self.frames,'flight_bounds':[self.flight_rect().left(),self.flight_rect().top(),self.flight_rect().right(),self.flight_rect().bottom()],'positions_bounds':[round(min(b[0] for b in self.boids),2),round(min(b[1] for b in self.boids),2),round(max(b[0] for b in self.boids),2),round(max(b[1] for b in self.boids),2)],'simulation_seconds':round(self.sim_seconds,4),'uptime':round(time.monotonic()-self.started,1)}))
    def step(self):
        now=time.monotonic(); dt=min(now-self.last,.1); self.last=now; begin=time.perf_counter()
        old=[b[:] for b in self.boids]; W=self.width(); H=self.height(); bounds=self.flight_rect()
        # A spatial grid keeps neighbour work local as the flock grows.
        radius=self.cfg['radius'];grid={}
        for i,b in enumerate(old): grid.setdefault((int(b[0]//radius),int(b[1]//radius)),[]).append(i)
        for i,b in enumerate(self.boids):
            px,py,vx,vy=old[i]; n=0; ax=ay=cx=cy=sx=sy=0.
            gx,gy=int(px//radius),int(py//radius)
            for xx in range(gx-1,gx+2):
                for yy in range(gy-1,gy+2):
                    for j in grid.get((xx,yy),()):
                        if i==j: continue
                        ox,oy,ovx,ovy=old[j]; dx=ox-px; dy=oy-py; d2=dx*dx+dy*dy
                        if 0<d2<radius*radius:
                            n+=1; ax+=ovx; ay+=ovy; cx+=dx; cy+=dy
                            if d2<min(25,radius*.3)**2: sx-=dx/max(d2,1); sy-=dy/max(d2,1)
            if n:
                vx+=((ax/n-vx)*.65*self.cfg['alignment']/100+cx/n*.35*self.cfg['cohesion']/100+sx*650*self.cfg['separation']/100)*dt
                vy+=((ay/n-vy)*.65*self.cfg['alignment']/100+cy/n*.35*self.cfg['cohesion']/100+sy*650*self.cfg['separation']/100)*dt
            # Anticipate walls and steer into the safe area well before arrival.
            # Lookahead scales with speed, so fast birds can turn without bouncing.
            desired_speed=self.cfg['speed']
            margin=min(32,bounds.width()/4,bounds.height()/4)
            lookahead=.35
            future_x=px+vx*lookahead;future_y=py+vy*lookahead
            wall_x=max(0,(bounds.left()+margin-future_x)/margin)-max(0,(future_x-bounds.right()+margin)/margin)
            wall_y=max(0,(bounds.top()+margin-future_y)/margin)-max(0,(future_y-bounds.bottom()+margin)/margin)
            vx+=wall_x*desired_speed*3*dt;vy+=wall_y*desired_speed*3*dt
            speed=math.hypot(vx,vy) or 1
            target=max(desired_speed*.7,min(desired_speed*1.4,speed));vx*=target/speed;vy*=target/speed
            nx=px+vx*dt;ny=py+vy*dt
            # A final safety envelope prevents panel overlap after resizing or
            # extreme slider changes. Remove outward velocity rather than reflect.
            if nx<bounds.left():nx=bounds.left();vx=max(0,vx)
            if nx>bounds.right():nx=bounds.right();vx=min(0,vx)
            if ny<bounds.top():ny=bounds.top();vy=max(0,vy)
            if ny>bounds.bottom():ny=bounds.bottom();vy=min(0,vy)
            b[:]=[nx,ny,vx,vy]
        self.update(); self.frames+=1; self.sim_seconds+=time.perf_counter()-begin
    def paintEvent(self,event):
        if not self.cfg['enabled']:return
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        colors=[QColor('#8bb9c5'),QColor('#b9d5cb'),QColor('#c7ba94')]
        for i,(x,y,vx,vy) in enumerate(self.boids):
            if not event.region().intersects(QRect(int(x)-24,int(y)-24,49,49)): continue
            length=math.hypot(vx,vy) or 1; ux,uy=vx/length,vy/length
            scale=self.cfg['size']/7;ux*=scale;uy*=scale
            p.setBrush(colors[i%3]); p.drawPolygon(QPolygonF([QPointF(x+ux*7,y+uy*7),QPointF(x-ux*5-uy*3,y-uy*5+ux*3),QPointF(x-ux*2,y-uy*2),QPointF(x-ux*5+uy*3,y-uy*5-ux*3)]))

app=QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
w=Wallpaper()
# Prebuild controls in the running Qt process; hover never cold-starts Python.
controls=Controls(persistent=True)
controls.hide()
control_socket=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
socket_path=runtime/'controls.sock';socket_path.unlink(missing_ok=True)
control_socket.bind(str(socket_path));control_socket.setblocking(False)
notifier=QSocketNotifier(control_socket.fileno(),QSocketNotifier.Read)
def control_message(*_):
    while True:
        try:msg=json.loads(control_socket.recv(8192))
        except BlockingIOError:break
        except (ValueError,OSError):continue
        if msg.get('action')=='show':
            cfg=load();controls.cfg=cfg
            for key,slider in controls.sliders.items():
                slider.blockSignals(True);slider.setValue(cfg[key]);slider.blockSignals(False);controls.update_label(key,cfg[key])
            controls.move(int(msg['x']),int(msg['y']));controls.show();controls.raise_()
            (runtime/'controls.geometry').write_text(json.dumps([controls.x(),controls.y(),controls.width(),controls.height()]))
        elif msg.get('action')=='hide':controls.hide()
notifier.activated.connect(control_message)
app.aboutToQuit.connect(lambda:socket_path.unlink(missing_ok=True))
signal.signal(signal.SIGTERM,lambda *_:app.quit())
signal.signal(signal.SIGINT,lambda *_:app.quit())
sys.exit(app.exec_())
