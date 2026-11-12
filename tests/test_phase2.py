from dataclasses import asdict
from pathlib import Path
import json
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from playx.core import Track,plan,render,load_plan
from playx.midi import envelope,STYLES
from playx.quality import inspect
from playx.studio import app


def track(bpm=120.,duration=60.):
    return Track('dummy',duration,bpm,'A minor',[.1+i*60/bpm for i in range(int(duration*bpm/60))],.2)


def test_half_time_and_tempo_ratio():
    p=plan(track(140),track(70))
    assert p.tempo_sync and p.tempo_ratio==1
    p=plan(track(120),track(132))
    assert .9<p.tempo_ratio<1 and p.tempo_sync
    assert plan(track(120),track(160)).tempo_sync is False
    assert plan(track(120),track(132),tempo_sync=False).tempo_ratio==1


def test_phrase_candidate_and_json(tmp_path):
    p=plan(track(),track(),bars=4)
    assert p.start_a in track().beats
    path=tmp_path/'p.json'
    from playx.core import save_json
    save_json(p,path)
    assert load_plan(path)==p


def test_envelopes():
    for style in STYLES:
        assert envelope(style,0)==0
        assert envelope(style,1)==1
        assert all(0<=envelope(style,x)<=1 for x in np.linspace(0,1,20))
    with pytest.raises(ValueError):envelope('unknown',.3)


def test_quality_with_silence(tmp_path):
    p=tmp_path/'quiet.wav'
    sf.write(p,np.zeros(44100),44100)
    q=inspect(p,tmp_path/'q.json')
    assert q['quiet_window_fraction']==1
    assert len(q['warnings'])>0
    assert json.loads((tmp_path/'q.json').read_text())==q


def test_actual_pitch_preserving_tempo_sync(tmp_path):
    sr=22050
    t=np.arange(sr*5)/sr
    a=.2*np.sin(2*np.pi*230*t)
    b=.2*np.sin(2*np.pi*430*t)
    pa,pb=tmp_path/'a.wav',tmp_path/'b.wav'
    sf.write(pa,a,sr);sf.write(pb,b,sr)
    ta=track(120,5);tb=track(132,5)
    pl=plan(ta,tb,bars=4)
    out=tmp_path/'output.wav'
    report=render(str(pa),str(pb),pl,str(out))
    assert report['tempo_synced'] is True
    assert Path(report['quality_report']).is_file()
    assert report['quality']['samples_near_clipping']==0
    data,_=sf.read(out)
    assert np.max(abs(data))<=.971


def test_local_studio_only():
    client=TestClient(app)
    response=client.get('/')
    assert response.status_code==200 and 'PLAYX' in response.text
    assert client.post('/api/mix',json={'a':'missing1','b':'missing2'}).status_code==400
    assert client.post('/api/mix',json={'a':'x','b':'y','energy':2}).status_code==422
