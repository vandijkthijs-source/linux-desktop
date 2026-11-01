#!/usr/bin/python3
import fcntl
import os
from pathlib import Path
import sys
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QPushButton
from settings import load,save,DEFAULTS,LIMITS
runtime=Path(os.environ.get('XDG_RUNTIME_DIR','/tmp'))/('desktop-boids-'+str(os.getuid()))
runtime.mkdir(mode=0o700,exist_ok=True)
class Controls(QWidget):
    def __init__(self, persistent=False):
        self.persistent=persistent
        super().__init__(None,(Qt.Tool|Qt.X11BypassWindowManagerHint|Qt.WindowStaysOnTopHint|Qt.FramelessWindowHint) if persistent else (Qt.Popup|Qt.FramelessWindowHint))
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle('Flock settings');self.setObjectName('flockSettings');self.setFixedWidth(340)
        self.setStyleSheet('''QWidget#flockSettings {background:#20262e;border:1px solid #3b4654;border-radius:10px;} QLabel{color:#f5f7fb;font:10pt "DejaVu Sans";border:0;} QSlider::groove:horizontal{height:4px;background:#3b4654;border-radius:2px;} QSlider::sub-page:horizontal{background:#77d19b;border-radius:2px;} QSlider::handle:horizontal{background:#b9d5cb;width:13px;margin:-5px 0;border-radius:6px;} QPushButton{color:#f5f7fb;background:#2c3540;border:1px solid #3b4654;padding:7px;border-radius:5px;} QPushButton:hover{background:#364150;}''')
        self.cfg=load();self.sliders={};self.labels={};self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.timeout.connect(self.persist)
        layout=QVBoxLayout(self);layout.setContentsMargins(16,14,16,14);layout.setSpacing(8)
        title=QLabel('Flock settings');title.setStyleSheet('font-weight:bold;font-size:12pt');layout.addWidget(title)
        rows=[('count','Birds','Number of birds'),('speed','Speed','How fast the flock moves'),('separation','Personal space','How strongly birds avoid one another'),('alignment','Follow direction','How strongly birds match their neighbours’ direction'),('cohesion','Stay together','How strongly birds move toward their neighbours'),('radius','Neighbour distance','How far each bird can see'),('size','Bird size','Size of each bird'),('fps','Smoothness','Frames per second; higher uses more power')]
        for key,name,tip in rows:
            line=QHBoxLayout();label=QLabel(name);value=QLabel();value.setAlignment(Qt.AlignRight);line.addWidget(label);line.addWidget(value);layout.addLayout(line)
            slider=QSlider(Qt.Horizontal);slider.setRange(*LIMITS[key]);slider.setValue(self.cfg[key]);slider.setToolTip(tip);layout.addWidget(slider)
            self.labels[key]=value;self.sliders[key]=slider;self.update_label(key,slider.value())
            slider.valueChanged.connect(lambda v,k=key:self.changed(k,v))
        note=QLabel('Pauses when fully covered • lower FPS on battery');note.setStyleSheet('color:#aeb9c8;font-size:8pt');layout.addWidget(note)
        buttons=QHBoxLayout();reset=QPushButton('Reset');reset.clicked.connect(self.reset);done=QPushButton('Done');done.clicked.connect(self.close);buttons.addWidget(reset);buttons.addWidget(done);layout.addLayout(buttons)
        self.adjustSize();pos=QCursor.pos();screen=QApplication.instance().screenAt(pos) or QApplication.primaryScreen();area=screen.availableGeometry()
        self.move(max(area.left(),min(pos.x()-self.width()//2,area.right()-self.width())),max(area.top(),screen.geometry().top()+43))
    def update_label(self,key,value):
        suffix='%' if key in ('separation','alignment','cohesion') else ' fps' if key=='fps' else ''
        self.labels[key].setText(str(value)+suffix)
    def changed(self,key,value):
        self.cfg[key]=value;self.update_label(key,value);self.debounce.start(100)
    def persist(self):
        # Preserve a panel toggle made while this popup was open.
        self.cfg['enabled']=load()['enabled'];save(self.cfg)
    def reset(self):
        for key,slider in self.sliders.items():slider.setValue(DEFAULTS[key])
    def hideEvent(self,event):
        if self.debounce.isActive():self.persist()
        if not self.persistent:QTimer.singleShot(0,QApplication.instance().quit)
        super().hideEvent(event)
    def closeEvent(self,event):
        if self.debounce.isActive():self.persist()
        if self.persistent:event.ignore();self.hide()
        else:super().closeEvent(event)
if __name__=='__main__':
    lock=(runtime/'settings.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:sys.exit(0)
    app=QApplication(sys.argv);w=Controls();w.show();sys.exit(app.exec_())
