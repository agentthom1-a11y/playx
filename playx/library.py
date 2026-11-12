"""Music discovery and explainable set recommendations, no automatic copyrighted uploads."""
from dataclasses import asdict
from pathlib import Path
from math import exp, log
from .core import analyze

AUDIO_EXTENSIONS = {'.wav','.flac','.aif','.aiff','.mp3','.ogg'}
NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']


def key_distance(left, right):
    """Harmonic compatibility heuristic: same key, relative major/minor, fifth, or adjacent."""
    def parse(key):
        if key == 'unknown': return None
        parts = key.split(' ')
        if len(parts)!=2 or parts[0] not in NOTES or parts[1] not in ('major','minor'):return None
        return NOTES.index(parts[0]),parts[1]
    a,b=parse(left),parse(right)
    if a is None or b is None:return .5
    diff=(b[0]-a[0])%12
    if a==b:return 0.
    if a[1]!=b[1] and diff==(9 if a[1]=='major' else 3):return .05
    if a[1]==b[1] and diff in (5,7):return .15
    if diff in (1,11):return .5
    return 1.


def compatibility(a,b):
    bpm_ratio=min(abs(log(a.bpm/(b.bpm*f))) for f in (.5,1.,2.))
    bpmscore=exp(-5*bpm_ratio)
    keyscore=1.-key_distance(a.key,b.key)
    energyscore=exp(-4*abs(a.energy-b.energy))
    return round(.5*bpmscore+.3*keyscore+.2*energyscore,4)


def recommend(paths, limit=8, profile='wave'):
    if not 2<=limit<=30:raise ValueError('limit must be in [2,30]')
    if profile not in ('wave','build','chill'):raise ValueError('unknown energy profile')
    files=[]
    for path in paths:
        p=Path(path).expanduser()
        if p.is_dir():files.extend(f for f in p.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS)
        elif p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:files.append(p)
    files=sorted(set(str(p.resolve()) for p in files))
    if len(files)<2:raise ValueError('Need at least two supported audio files')
    if len(files)>100:raise ValueError('Limit a planning batch to 100 tracks for predictable CPU use')
    tracks=[]; failures=[]
    for file in files:
        try:tracks.append(analyze(file))
        except (ValueError,OSError,RuntimeError) as e:failures.append({'file':file,'reason':str(e)[:160]})
    if len(tracks)<2:raise ValueError('Fewer than two analyzable tracks')
    order=sorted(range(len(tracks)),key=lambda i:tracks[i].energy)
    chosen=[order[0] if profile=='build' else order[-1] if profile=='chill' else order[len(order)//2]]
    while len(chosen)<min(limit,len(tracks)):
        left=tracks[chosen[-1]]
        target=len(chosen)/max(1,min(limit,len(tracks))-1)
        if profile=='build':target_energy=tracks[order[0]].energy+(tracks[order[-1]].energy-tracks[order[0]].energy)*target
        elif profile=='chill':target_energy=tracks[order[-1]].energy+(tracks[order[0]].energy-tracks[order[-1]].energy)*target
        else:target_energy=tracks[order[0]].energy+(tracks[order[-1]].energy-tracks[order[0]].energy)*(.5+.5*__import__('math').sin(target*2*__import__('math').pi))
        nxt=max((i for i in range(len(tracks)) if i not in chosen),key=lambda i: .75*compatibility(left,tracks[i])-.25*abs(tracks[i].energy-target_energy))
        chosen.append(nxt)
    result=[]
    for index,i in enumerate(chosen):
        item=asdict(tracks[i]);item['order']=index+1
        if index:item['compatibility_with_previous']=compatibility(tracks[chosen[index-1]],tracks[i])
        result.append(item)
    return {'profile':profile,'tracks':result,'skipped':failures,'note':'A heuristic suggestion, not validated harmonic mixing or autonomous playback'}
