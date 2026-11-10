#!/usr/bin/python3
"""Preloaded X11 icon switcher. Input is grabbed only while its menu is visible."""
import array
import ctypes as C
import fcntl
import os
from pathlib import Path
import socket
import sys
from PyQt5 import QtCore, QtGui, QtWidgets

RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
SOCKET = RUNTIME / 'desktop-alt-tab-warm.sock'

class ClientData(C.Union):
    _fields_ = [('b', C.c_char * 20), ('s', C.c_short * 10), ('l', C.c_long * 5)]
class ClientMessage(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', C.c_ulong), ('send_event', C.c_int),
                ('display', C.c_void_p), ('window', C.c_ulong), ('message_type', C.c_ulong),
                ('format', C.c_int), ('data', ClientData)]
class PropertyEvent(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', C.c_ulong), ('send_event', C.c_int),
                ('display', C.c_void_p), ('window', C.c_ulong), ('atom', C.c_ulong),
                ('time', C.c_ulong), ('state', C.c_int)]
class Event(C.Union):
    _fields_ = [('client', ClientMessage), ('property', PropertyEvent), ('pad', C.c_long * 24)]
class ClassHint(C.Structure):
    _fields_ = [('name', C.c_char_p), ('klass', C.c_char_p)]

class X11:
    def __init__(self):
        self.x = C.CDLL('libX11.so.6')
        signatures = {
            'XOpenDisplay': ([C.c_char_p], C.c_void_p),
            'XDefaultRootWindow': ([C.c_void_p], C.c_ulong),
            'XInternAtom': ([C.c_void_p, C.c_char_p, C.c_int], C.c_ulong),
            'XGetWindowProperty': ([C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.c_void_p)], C.c_int),
            'XFree': ([C.c_void_p], C.c_int),
            'XSelectInput': ([C.c_void_p,C.c_ulong,C.c_long], C.c_int),
            'XConnectionNumber': ([C.c_void_p], C.c_int),
            'XPending': ([C.c_void_p], C.c_int),
            'XNextEvent': ([C.c_void_p,C.POINTER(Event)], C.c_int),
            'XFlush': ([C.c_void_p], C.c_int),
            'XQueryKeymap': ([C.c_void_p,C.c_void_p], C.c_int),
            'XKeysymToKeycode': ([C.c_void_p,C.c_ulong], C.c_ubyte),
            'XSendEvent': ([C.c_void_p,C.c_ulong,C.c_int,C.c_long,C.POINTER(Event)], C.c_int),
            'XSetClassHint': ([C.c_void_p,C.c_ulong,C.POINTER(ClassHint)], C.c_int),
        }
        for name,(args,result) in signatures.items():
            func=getattr(self.x,name);func.argtypes=args;func.restype=result
        # Windows may disappear between a root notification and a property read.
        self.error_callback=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)(lambda *_: 0)
        self.x.XSetErrorHandler.argtypes=[C.c_void_p]
        self.x.XSetErrorHandler(C.cast(self.error_callback,C.c_void_p))
        self.d=self.x.XOpenDisplay(None)
        if not self.d: raise RuntimeError('X11 display unavailable')
        self.root=self.x.XDefaultRootWindow(self.d)
        self.atoms={}
        self.alt=[self.x.XKeysymToKeycode(self.d,key) for key in (0xffe9,0xffea)]
        self.keys=C.create_string_buffer(32)
    def atom(self,name):
        if name not in self.atoms:self.atoms[name]=self.x.XInternAtom(self.d,name.encode(),False)
        return self.atoms[name]
    def prop(self,wid,name,limit=262144):
        typ=C.c_ulong();fmt=C.c_int();n=C.c_ulong();left=C.c_ulong();data=C.c_void_p()
        status=self.x.XGetWindowProperty(self.d,wid,self.atom(name),0,limit,False,0,C.byref(typ),C.byref(fmt),C.byref(n),C.byref(left),C.byref(data))
        if status or not data.value:return []
        try:
            if fmt.value==32:return list(C.cast(data,C.POINTER(C.c_ulong))[:n.value])
            if fmt.value==8:return C.string_at(data,n.value)
            return []
        finally:self.x.XFree(data)
    def alt_held(self):
        self.x.XQueryKeymap(self.d,self.keys)
        return any(self.keys.raw[k//8] & (1<<(k%8)) for k in self.alt)
    def activate(self,wid):
        e=Event();e.client.type=33;e.client.display=self.d;e.client.window=wid
        e.client.message_type=self.atom('_NET_ACTIVE_WINDOW');e.client.format=32
        e.client.data.l[0]=2
        self.x.XSendEvent(self.d,self.root,False,(1<<19)|(1<<20),C.byref(e));self.x.XFlush(self.d)
    def icon(self,wid):
        values=self.prop(wid,'_NET_WM_ICON');candidates=[];pos=0
        while pos+2<=len(values):
            w,h=values[pos:pos+2];start=pos+2;end=start+w*h
            if not w or not h or end>len(values):break
            if w<=512 and h<=512:candidates.append((abs(max(w,h)-64),w,h,start,end))
            pos=end
        if candidates:
            _,w,h,start,end=min(candidates)
            pixels=array.array('I',(p&0xffffffff for p in values[start:end]))
            image=QtGui.QImage(pixels.tobytes(),w,h,w*4,QtGui.QImage.Format_ARGB32).copy()
            return QtGui.QPixmap.fromImage(image)
        klass=self.prop(wid,'WM_CLASS')
        name=klass.split(b'\0')[0].decode(errors='replace').split(' (',1)[0] if isinstance(klass,bytes) else ''
        if '/' not in name:
            for suffix in ('.png','.svg','.xpm'):
                path=Path('/usr/share/pixmaps')/(name+suffix)
                if path.is_file():return QtGui.QIcon(str(path)).pixmap(64,64)
        icon=QtGui.QIcon.fromTheme(name,QtGui.QIcon.fromTheme('application-x-executable'))
        return icon.pixmap(64,64)

class Switcher(QtWidgets.QWidget):
    def __init__(self,x):
        super().__init__(None,QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint|QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.X11BypassWindowManagerHint|QtCore.Qt.WindowDoesNotAcceptFocus)
        self.x=x;self.cache={};self.order=[];self.items=[];self.index=0
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.setWindowTitle('Desktop Alt Tab')
        hint=ClassHint(b'desktop-alt-tab',b'DesktopAltTab')
        self.x.x.XSetClassHint(self.x.d,int(self.winId()),C.byref(hint));self.x.x.XFlush(self.x.d)
        self.timer=QtCore.QTimer(self);self.timer.setInterval(5);self.timer.timeout.connect(self.check_alt)
        self.refresh_timer=QtCore.QTimer(self);self.refresh_timer.setSingleShot(True);self.refresh_timer.timeout.connect(self.refresh)
        self.x.x.XSelectInput(self.x.d,self.x.root,1<<22);self.x.x.XFlush(self.x.d)
        self.events=QtCore.QSocketNotifier(self.x.x.XConnectionNumber(self.x.d),QtCore.QSocketNotifier.Read,self)
        self.events.activated.connect(self.root_events)
        self.refresh()
    def root_events(self):
        relevant={self.x.atom('_NET_CLIENT_LIST_STACKING'),self.x.atom('_NET_CLIENT_LIST'),self.x.atom('_NET_ACTIVE_WINDOW')}
        while self.x.x.XPending(self.x.d):
            event=Event();self.x.x.XNextEvent(self.x.d,C.byref(event))
            if event.property.type==28 and event.property.atom in relevant:self.refresh_timer.start(60)
    def refresh(self):
        ids=self.x.prop(self.x.root,'_NET_CLIENT_LIST_STACKING')
        skip=self.x.atom('_NET_WM_STATE_SKIP_TASKBAR')
        excluded={self.x.atom('_NET_WM_WINDOW_TYPE_DESKTOP'),self.x.atom('_NET_WM_WINDOW_TYPE_DOCK')}
        order=[]
        for wid in reversed(ids):
            if skip in self.x.prop(wid,'_NET_WM_STATE') or excluded.intersection(self.x.prop(wid,'_NET_WM_WINDOW_TYPE')):continue
            order.append(wid)
            if wid not in self.cache:self.cache[wid]=self.x.icon(wid)
        self.order=order;self.cache={w:self.cache[w] for w in order}
    def open_menu(self,direction):
        if self.isVisible():self.step(direction);return
        if not self.order:self.refresh()
        active=self.x.prop(self.x.root,'_NET_ACTIVE_WINDOW')
        current=active[0] if active else 0
        self.items=([current] if current in self.order else [])+[w for w in self.order if w!=current]
        if not self.items:return
        self.index=(direction%len(self.items)) if current in self.items else 0
        columns=min(len(self.items),6);rows=(len(self.items)+columns-1)//columns
        self.resize(24+columns*100,24+rows*84+(rows-1)*8)
        screen=QtWidgets.QApplication.screenAt(QtGui.QCursor.pos()) or QtWidgets.QApplication.primaryScreen()
        rect=screen.availableGeometry();self.move(rect.center()-self.rect().center())
        self.show();self.raise_();self.grabKeyboard();self.timer.start();self.update()
    def step(self,direction):
        if self.items:self.index=(self.index+direction)%len(self.items);self.update()
    def finish(self,choose):
        if not self.isVisible():return
        wid=self.items[self.index] if choose and self.items else None
        self.timer.stop();self.releaseKeyboard();self.hide()
        if wid:self.x.activate(wid)
    def check_alt(self):
        if not self.x.alt_held():self.finish(True)
    def event(self,e):
        if self.isVisible() and e.type()==QtCore.QEvent.KeyPress:
            key=e.key()
            if key in (QtCore.Qt.Key_Tab,QtCore.Qt.Key_Backtab):
                self.step(-1 if key==QtCore.Qt.Key_Backtab or e.modifiers()&QtCore.Qt.ShiftModifier else 1);return True
            if key in (QtCore.Qt.Key_Left,QtCore.Qt.Key_Up):self.step(-1);return True
            if key in (QtCore.Qt.Key_Right,QtCore.Qt.Key_Down):self.step(1);return True
            if key==QtCore.Qt.Key_Escape:self.finish(False);return True
            if key in (QtCore.Qt.Key_Return,QtCore.Qt.Key_Enter):self.finish(True);return True
        return super().event(e)
    def card(self,i):
        cols=min(len(self.items),6);row,col=divmod(i,cols)
        return QtCore.QRectF(12+col*100,12+row*92,90,84)
    def mousePressEvent(self,e):
        for i in range(len(self.items)):
            if self.card(i).contains(e.pos()):self.index=i;self.finish(True);break
    def paintEvent(self,e):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(QtGui.QPen(QtGui.QColor(255,255,255,128),1));p.setBrush(QtGui.QColor(238,233,243,118))
        p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),20,20)
        for i,wid in enumerate(self.items):
            card=self.card(i)
            if i==self.index:
                p.setPen(QtGui.QPen(QtGui.QColor('#476fae'),3));p.setBrush(QtGui.QColor(255,255,255,232))
                p.drawRoundedRect(card.adjusted(1.5,1.5,-1.5,-1.5),12,12)
            icon=self.cache.get(wid)
            if icon and not icon.isNull():
                target=QtCore.QRectF(card.center().x()-28,card.center().y()-28,56,56)
                p.drawPixmap(target,icon,QtCore.QRectF(icon.rect()))

app=QtWidgets.QApplication(sys.argv);app.setQuitOnLastWindowClosed(False)
app.setApplicationName('DesktopAltTab')
QtGui.QIcon.setThemeName('Papirus')
lock=open(RUNTIME/'desktop-alt-tab-service.lock','w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit(0)
x=X11();menu=Switcher(x)
sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
SOCKET.unlink(missing_ok=True);sock.bind(str(SOCKET));os.chmod(SOCKET,0o600);sock.setblocking(False)
notifier=QtCore.QSocketNotifier(sock.fileno(),QtCore.QSocketNotifier.Read)
def receive():
    while True:
        try:command=sock.recv(64).decode().strip()
        except BlockingIOError:return
        if command=='next':menu.open_menu(1)
        elif command=='prev':menu.open_menu(-1)
        elif command=='cancel':menu.finish(False)
        elif command=='quit':menu.finish(False);app.quit()
notifier.activated.connect(receive)
try:raise SystemExit(app.exec_())
finally:SOCKET.unlink(missing_ok=True)
