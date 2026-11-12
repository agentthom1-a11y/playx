from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
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
    tempo_sync: bool = True
    tempo_ratio: float = 1.0

def analyze(path: str) -> Track:
    import librosa
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    y, sr = librosa.load(str(p), sr=22050, mono=True)
    if y.size < sr * 2:
        raise ValueError('Audio must be at least two seconds')
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    bpm = float(np.asarray(tempo).reshape(-1)[0])
    bpm = bpm if np.isfinite(bpm) and bpm > 20 else 120.0
    beats = librosa.frames_to_time(frames, sr=sr).tolist()
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_avg = np.mean(chroma, axis=1)
    names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    major = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
    minor = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
    scores = [(float(np.corrcoef(chroma_avg, np.roll(profile, i))[0,1]), names[i] + suffix)
              for i in range(12) for profile, suffix in ((major,' major'),(minor,' minor'))]
    key = max(scores)[1] if np.std(chroma_avg) > 1e-6 else 'unknown'
    return Track(str(p), round(len(y)/sr, 3), round(bpm,2), key,
                 [round(float(t),3) for t in beats], round(float(np.sqrt(np.mean(y*y))),4))

def plan(a: Track, b: Track, style='auto', energy=0.7, bars=8, tempo_sync=True) -> Plan:
    if not 0 <= energy <= 1: raise ValueError('energy must be in [0,1]')
    if bars not in (4,8,16,32): raise ValueError('bars must be 4, 8, 16 or 32')
    styles = ('smooth','bass_swap','filter_sweep','echo_out','drop_swap')
    if style not in (*styles,'auto'): raise ValueError('Unknown style')
    if min(a.bpm,b.bpm) <= 0: raise ValueError('BPM must be positive')
    # Handle common half/double-time analysis errors before stretching.
    ratio = min((a.bpm / (b.bpm * factor) for factor in (0.5, 1.0, 2.0)), key=lambda x: abs(np.log(x)))
    can_sync = bool(tempo_sync and 0.80 <= ratio <= 1.25)
    delta = abs(1.0-ratio)
    chosen = style if style != 'auto' else ('echo_out' if delta > 0.12 else 'drop_swap' if energy > .85 else 'bass_swap' if energy > .6 else 'smooth')
    bpm = a.bpm
    duration = 4*bars*60/bpm
    # A plays until the transition; B starts at a detected downbeat near its beginning.
    start_a = max(0.0, a.duration-duration)
    if a.beats:
        # Approximate 4-bar phrase boundaries assuming 4/4; not a true downbeat model.
        candidates = [t for i,t in enumerate(a.beats) if i % 16 == 0 and t <= start_a]
        if candidates: start_a = candidates[-1]
        else:
            valid = [t for t in a.beats if t <= start_a]
            if valid: start_a = valid[-1]
    start_b = b.beats[0] if b.beats else 0.0
    if start_a + duration > a.duration: duration = a.duration-start_a
    if duration <= 0: raise ValueError('Track A too short for transition')
    return Plan(chosen,bars,round(bpm,2),round(start_a,3),round(start_b,3),round(duration,3),
                f'BPM gap {delta:.1%}; {bars}-bar phrase approximation; energy {energy:.2f}. Verify by ear.',
                can_sync, round(ratio,6) if can_sync else 1.0)

def save_json(obj, path):
    Path(path).write_text(json.dumps(asdict(obj), indent=2), encoding='utf-8')

def load_plan(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    return Plan(**data)

def render(a_path: str, b_path: str, p: Plan, out: str) -> dict:
    import soundfile as sf
    from scipy.signal import butter, sosfilt
    sr=44100
    def read(path):
        import librosa
        y, _ = librosa.load(path, sr=sr, mono=False)
        return y[np.newaxis,:] if y.ndim == 1 else y[:2]
    a,b=read(a_path),read(b_path)
    channels=max(a.shape[0],b.shape[0])
    if a.shape[0] != channels: a=np.repeat(a,channels,axis=0)
    if b.shape[0] != channels: b=np.repeat(b,channels,axis=0)
    ia=round(p.start_a*sr); ib=round(p.start_b*sr); n=round(p.duration*sr)
    if ia < 0 or ib < 0 or n < 1 or ia >= a.shape[1] or ib >= b.shape[1]:
        raise ValueError('Transition out of track bounds')
    # Stretch the incoming track once, before applying the transition.
    # librosa keeps pitch approximately constant. This is CPU/memory intensive for long tracks.
    if p.tempo_sync and abs(p.tempo_ratio-1)>1e-4:
        import librosa
        if not 0.8 <= p.tempo_ratio <= 1.25:
            raise ValueError('Unsafe tempo ratio in plan')
        b=librosa.effects.time_stretch(b[:,ib:],rate=p.tempo_ratio)
        ib=0
    n=min(n,a.shape[1]-ia,b.shape[1]-ib)
    if n < 2: raise ValueError('Transition too short')
    t=np.linspace(0,1,n,endpoint=True)
    # Equal-power envelopes; some styles use more abrupt curves.
    x=np.sin(np.pi*t/2)**2
    if p.style == 'drop_swap': x=(t>=.5).astype(float)
    if p.style == 'echo_out': x=np.clip((t-.65)/.35,0,1)
    if p.style == 'bass_swap': x=np.clip((t-.25)/.5,0,1)
    if p.style == 'filter_sweep': x=t*t*(3-2*t)
    wa=np.cos(x*np.pi/2)[None,:]
    wb=np.sin(x*np.pi/2)[None,:]
    aa=a[:,ia:ia+n].copy(); bb=b[:,ib:ib+n].copy()
    if p.style == 'bass_swap':
        lp=butter(2,180,fs=sr,output='sos')
        low_a=sosfilt(lp,aa,axis=1)
        low_b=sosfilt(lp,bb,axis=1)
        eq=np.clip((t-.25)/.5,0,1)[None,:]
        aa-=low_a*eq
        bb-=low_b*(1-eq)
    if p.style == 'filter_sweep':
        low=sosfilt(butter(2,1200,fs=sr,output='sos'),aa,axis=1)
        aa=aa*(1-t)[None,:]+low*t[None,:]
    if p.style == 'echo_out':
        # Simple decay tail without introducing an unbounded delay buffer.
        delay=round(.375*sr)
        for k in (1,2,3):
            if k*delay<n:
                aa[:,k*delay:]+=aa[:,:n-k*delay]*(0.22**k)
    overlap=aa*wa+bb*wb
    # Preserve full A intro and full B outro, not merely a short preview.
    result=np.concatenate((a[:,:ia],overlap,b[:,ib+n:]),axis=1)
    peak=float(np.max(np.abs(result)))
    gain=min(1.0,0.97/peak) if peak else 1.0
    result=(result*gain).T.astype('float32')
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    sf.write(out,result,sr,subtype='PCM_24')
    from .quality import assess
    report=assess(str(Path(out).resolve()), seam_seconds=[ia/sr,(ia+n)/sr])
    report_path=Path(str(out)+'.quality.json')
    report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {'output':str(Path(out).resolve()),'duration':round(len(result)/sr,2),
            'sample_rate':sr,'peak_before_gain':round(peak,4),'gain':round(gain,4),
            'tempo_synced':bool(p.tempo_sync and abs(p.tempo_ratio-1)>1e-4),
            'quality_report':str(report_path.resolve()),'quality':report,
            'warning':'Estimated BPM/phrase alignment. Key matching and true-peak limiting are not implemented.'}
