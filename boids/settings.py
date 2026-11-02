"""Validated, shared flock preferences. All values are local to this user."""
import json
import os
from pathlib import Path
PATH=Path.home()/'.config/desktop-boids/settings.json'
DEFAULTS=dict(enabled=True,count=48,speed=48,separation=100,alignment=100,cohesion=100,radius=90,size=7,fps=15)
LIMITS=dict(count=(16,600),speed=(15,120),separation=(0,200),alignment=(0,200),cohesion=(0,200),radius=(40,180),size=(4,14),fps=(10,24))
def load():
    cfg=DEFAULTS.copy()
    try: data=json.loads(PATH.read_text())
    except (OSError,ValueError): return cfg
    if not isinstance(data,dict): return cfg
    if isinstance(data.get('enabled'),bool): cfg['enabled']=data['enabled']
    for key,(lo,hi) in LIMITS.items():
        value=data.get(key)
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            try: cfg[key]=max(lo,min(hi,int(value)))
            except (ValueError,OverflowError): pass
    return cfg
def save(cfg):
    PATH.parent.mkdir(parents=True,exist_ok=True)
    tmp=PATH.with_name(f'settings.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(tmp,PATH)
