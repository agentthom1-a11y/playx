from __future__ import annotations
import io
import json
import time
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from playx.core import Track, plan, render
from playx.library import key_distance, compatibility
from playx.studio import app


def wav_bytes(hz):
    sr=11025
    y=(0.1*np.sin(2*np.pi*hz*np.arange(sr*4)/sr)).astype('float32')
    result=io.BytesIO()
    sf.write(result,y,sr,format='WAV')
    return result.getvalue()


def test_upload_queue_render_download(tmp_path,monkeypatch):
    monkeypatch.setenv('PLAYX_DATA_DIR',str(tmp_path/'workspace'))
    with TestClient(app) as client:
        page=client.get('/')
        assert page.status_code==200 and 'Drop file or browse' in page.text
        assert client.get('/api/health').json()['remote_storage'] is False
        a=client.post('/api/uploads',files={'file':('first.wav',wav_bytes(220),'audio/wav')})
        b=client.post('/api/uploads',files={'file':('second.wav',wav_bytes(440),'audio/wav')})
        assert a.status_code==201 and b.status_code==201
        left,right=a.json(),b.json()
        assert len(left['waveform'])>0
        assert left['duration_seconds']==4
        job=client.post('/api/jobs',json={'a':left['id'],'b':right['id'],'style':'smooth','bars':4,'tempo_sync':False})
        assert job.status_code==202
        ident=job.json()['id']
        for _ in range(150):
            status=client.get('/api/jobs/'+ident).json()
            if status['state'] in ('done','failed'):break
            time.sleep(.08)
        assert status['state']=='done',status
        assert status['result']['quality']['sample_rate']==44100
        output=client.get('/api/jobs/'+ident+'/audio')
        assert output.status_code==200 and output.content[:4]==b'RIFF'
        quality=client.get('/api/jobs/'+ident+'/quality')
        assert quality.status_code==200 and 'peak_dbfs' in quality.json()
        assert client.delete('/api/uploads/'+left['id']).status_code==204
        assert client.get('/api/jobs/'+ident).json()['state']=='done'


def test_local_host_origin_and_invalid_upload(tmp_path,monkeypatch):
    monkeypatch.setenv('PLAYX_DATA_DIR',str(tmp_path/'workspace'))
    with TestClient(app) as client:
        assert client.get('/',headers={'host':'attacker.example'}).status_code==403
        assert client.post('/api/jobs',json={'a':'x','b':'y'},headers={'origin':'https://attacker.example'}).status_code==403
        assert client.post('/api/uploads',files={'file':('bad.exe',b'MZ','application/octet-stream')}).status_code==415
        assert client.post('/api/uploads',files={'file':('bad.wav',b'garbage','audio/wav')}).status_code==415
        assert client.post('/api/jobs',json={'a':'../x','b':'../y'}).status_code==404
        assert client.get('/api/jobs/../../etc/passwd').status_code in (404,405)


def test_plan_guard_prevents_overwrite(tmp_path):
    a,b=tmp_path/'a.wav',tmp_path/'b.wav'
    sf.write(a,np.zeros(44100*3),44100)
    sf.write(b,np.zeros(44100*3),44100)
    t=Track('dummy',3,120,'C major',[.25,.75,1.25,1.75,2.25],.01)
    p=plan(t,t,bars=4)
    output=tmp_path/'out.wav'
    render(str(a),str(b),p,str(output))
    with pytest.raises(FileExistsError):render(str(a),str(b),p,str(output))
    assert not any(f.name.startswith('.playx-') for f in tmp_path.iterdir())


def test_harmonic_heuristic():
    assert key_distance('C major','A minor') == .05
    assert key_distance('A minor','C major') == .05
    assert key_distance('C major','G major') == .15
    a=Track('a',80,120,'C major',[],.25)
    b=Track('b',80,122,'A minor',[],.26)
    c=Track('c',80,170,'F# minor',[],.7)
    assert compatibility(a,b) > compatibility(a,c)


def test_setmix_three_tracks(tmp_path):
    from playx.setmix import mix_set
    tracks=[]
    for i,freq in enumerate((220,330,440)):
        path=tmp_path/f'song-{i}.wav'
        sf.write(path,np.sin(np.arange(22050*11)*freq*2*np.pi/22050)*.1,22050)
        tracks.append(str(path))
    output=tmp_path/'set.wav'
    result=mix_set(tracks,str(output),bars=4,tempo_sync=False,style='smooth')
    assert result['track_count']==3
    assert sf.info(output).duration>11
    manifest=json.loads(Path(result['manifest']).read_text())
    assert len(manifest['transitions'])==2
    with pytest.raises(FileExistsError):mix_set(tracks,str(output),tempo_sync=False)
