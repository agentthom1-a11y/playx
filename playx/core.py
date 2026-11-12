from dataclasses import dataclass, asdict
from pathlib import Path
import json
import numpy as np

@dataclass
class Track:
    path: str
    duration: float
    bpm: float
    key: str
    beats: list[float]
    energy: float

@dataclass
class Plan:
    style: str
    bars: int
    bpm: float
    start_a: float
    start_b: float
    duration: float
    rationale: str

def analyze(path):
    import librosa
    p=Path(path).expanduser().resolve()
    if not p.is_file(): raise FileNotFoundError(p)
    y,sr=librosa.load(str(p),sr=22050,mono=True)
    if y.size<2*sr: raise ValueError("Audio must be at least two seconds")
    tempo,frames=librosa.beat.beat_track(y=y,sr=sr,trim=False)
    bpm=float(np.asarray(tempo).reshape(-1)[0])
    if not np.isfinite(bpm) or bpm<20: bpm=120.
    chroma=np.mean(librosa.feature.chroma_stft(y=y,sr=sr),axis=1)
    names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    major=np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
    minor=np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
    scores=[(float(np.corrcoef(chroma,np.roll(profile,i))[0,1]),names[i]+mode) for i in range(12) for profile,mode in ((major," major"),(minor," minor"))]
    key=max(scores)[1] if np.std(chroma)>1e-6 else "unknown"
    beats=librosa.frames_to_time(frames,sr=sr).tolist()
    return Track(str(p),round(len(y)/sr,3),round(bpm,2),key,[round(float(t),3) for t in beats],round(float(np.sqrt(np.mean(y*y))),4))

def plan(a,b,style="auto",energy=.7,bars=8):
    if not 0<=energy<=1: raise ValueError("energy must be 0..1")
    if bars not in (4,8,16,32): raise ValueError("bars must be 4, 8, 16, or 32")
    styles=("smooth","bass_swap","filter_sweep","echo_out","drop_swap")
    if style not in (*styles,"auto"): raise ValueError("unknown style")
    delta=abs(a.bpm-b.bpm)/max(a.bpm,b.bpm)
    chosen=style if style!="auto" else ("echo_out" if delta>.12 else "drop_swap" if energy>.85 else "bass_swap" if energy>.6 else "smooth")
    duration=4*bars*60/a.bpm
    start_a=max(0.,a.duration-duration)
    valid=[t for t in a.beats if t<=start_a]
    if valid: start_a=valid[-1]
    start_b=b.beats[0] if b.beats else 0.
    duration=min(duration,a.duration-start_a)
    if duration<=0: raise ValueError("track A too short")
    return Plan(chosen,bars,a.bpm,round(start_a,3),round(start_b,3),round(duration,3),f"BPM gap {delta:.1%}; check beat grid by ear")

def save_json(obj,path):
    Path(path).write_text(json.dumps(asdict(obj),indent=2),encoding="utf-8")

def load_plan(path):
    return Plan(**json.loads(Path(path).read_text(encoding="utf-8")))

def render(a_path,b_path,p,out):
    import librosa, soundfile as sf
    from scipy.signal import butter,sosfilt
    sr=44100
    def read(path):
        y,_=librosa.load(path,sr=sr,mono=False)
        return y[np.newaxis,:] if y.ndim==1 else y[:2]
    a,b=read(a_path),read(b_path)
    channels=max(a.shape[0],b.shape[0])
    if a.shape[0]!=channels: a=np.repeat(a,channels,axis=0)
    if b.shape[0]!=channels: b=np.repeat(b,channels,axis=0)
    ia=round(p.start_a*sr);ib=round(p.start_b*sr);n=round(p.duration*sr)
    if min(ia,ib)<0 or n<2 or ia>=a.shape[1] or ib>=b.shape[1]: raise ValueError("transition out of bounds")
    n=min(n,a.shape[1]-ia,b.shape[1]-ib)
    if n<2: raise ValueError("transition too short")
    t=np.linspace(0,1,n)
    x=np.sin(np.pi*t/2)**2
    if p.style=="drop_swap": x=(t>=.5).astype(float)
    if p.style=="echo_out": x=np.clip((t-.65)/.35,0,1)
    if p.style=="bass_swap": x=np.clip((t-.25)/.5,0,1)
    if p.style=="filter_sweep": x=t*t*(3-2*t)
    aa=a[:,ia:ia+n].copy();bb=b[:,ib:ib+n].copy()
    if p.style=="bass_swap":
        low=sosfilt(butter(2,180,fs=sr,output="sos"),aa,axis=1)
        aa-=low*np.clip((t-.25)/.5,0,1)[None,:]
    if p.style=="filter_sweep":
        low=sosfilt(butter(2,1200,fs=sr,output="sos"),aa,axis=1)
        aa=aa*(1-t)[None,:]+low*t[None,:]
    if p.style=="echo_out":
        delay=round(.375*sr)
        for k in (1,2,3):
            if k*delay<n: aa[:,k*delay:]+=aa[:,:n-k*delay]*(.22**k)
    overlap=aa*np.cos(x*np.pi/2)[None,:]+bb*np.sin(x*np.pi/2)[None,:]
    result=np.concatenate((a[:,:ia],overlap,b[:,ib+n:]),axis=1)
    peak=float(np.max(np.abs(result)))
    gain=min(1.,.97/peak) if peak else 1.
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    sf.write(out,(result*gain).T.astype("float32"),sr,subtype="PCM_24")
    return {"output":str(Path(out).resolve()),"duration":round(result.shape[1]/sr,2),"peak_before_gain":round(peak,4),"gain":round(gain,4),"warning":"Tempo/key are not corrected automatically"}
