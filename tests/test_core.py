import numpy as np
import soundfile as sf
import pytest
from playx.core import Track,plan,render,save_json,load_plan

def track(bpm=120,duration=60):
    return Track("dummy",duration,bpm,"A minor",[i*.5 for i in range(int(duration*2))],.2)

def test_plan():
    p=plan(track(),track(122),energy=.9)
    assert p.style=="drop_swap"
    assert p.duration>0
    assert p.start_a+p.duration<=60

def test_invalid():
    with pytest.raises(ValueError):plan(track(),track(),bars=3)
    with pytest.raises(ValueError):plan(track(),track(),energy=2)

def test_render(tmp_path):
    sr=44100
    t=np.arange(sr*5)/sr
    a=.15*np.sin(2*np.pi*220*t)
    b=.15*np.sin(2*np.pi*330*t)
    pa,pb=tmp_path/"a.wav",tmp_path/"b.wav"
    sf.write(pa,a,sr);sf.write(pb,b,sr)
    x=track(duration=5);x.beats=[.5,1,1.5,2,2.5,3,3.5,4,4.5]
    p=plan(x,x,bars=4)
    out=tmp_path/"mix.wav"
    result=render(str(pa),str(pb),p,str(out))
    y,rate=sf.read(out)
    assert rate==sr and len(y)>sr*4 and np.max(abs(y))<=.98
    assert result["duration"]>4
    save_json(p,tmp_path/"plan.json")
    assert load_plan(tmp_path/"plan.json")==p
