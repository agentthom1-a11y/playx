"""Bounded-memory sample-level audio QA. Not perceptual loudness or true-peak mastering."""
from pathlib import Path
import json
import math

import numpy as np
import soundfile as sf


def assess(path: str, seam_seconds=()):
    """Inspect multi-hour WAV files in chunks without loading the entire mix."""
    peak = 0.0
    squared = 0.0
    count = 0
    near_clipping = 0
    quiet = 0
    windows = 0
    with sf.SoundFile(path) as source:
        sr = source.samplerate
        channels = source.channels
        total_frames = len(source)
        if total_frames == 0:
            raise ValueError('Empty audio')
        win = max(1, sr // 10)
        # Chunking on full 100ms window boundaries makes the quiet ratio stable.
        frames_per_chunk = win * 100
        while True:
            chunk = source.read(frames_per_chunk, dtype='float32', always_2d=True)
            if not len(chunk):
                break
            data = chunk.astype('float64', copy=False)
            peak = max(peak, float(np.max(np.abs(data))))
            squared += float(np.sum(data * data))
            count += data.size
            near_clipping += int(np.count_nonzero(np.abs(data) >= .999))
            full = (len(chunk) // win) * win
            if full:
                rms = np.sqrt(np.mean(data[:full].reshape(-1, win, channels) ** 2, axis=(1, 2)))
                quiet += int(np.count_nonzero(rms < 10 ** (-50 / 20)))
                windows += len(rms)
        seams=[]
        for second in seam_seconds:
            idx=round(float(second)*sr)
            if 1 <= idx < total_frames:
                source.seek(idx-1)
                pair=source.read(2,dtype='float32',always_2d=True)
                seams.append({'at_seconds':round(float(second),3),
                              'jump':round(float(np.max(np.abs(pair[1]-pair[0]))),5)})
    rms = math.sqrt(squared / max(count,1))
    db = lambda x: round(20 * math.log10(max(x,1e-12)),2)
    silence = quiet / windows if windows else 0.0
    warnings=[]
    if peak >= .999: warnings.append('Sample peaks at/near digital full scale')
    if silence > .35: warnings.append('Large fraction of audio is quiet (< -50 dBFS)')
    if any(s['jump'] > .7 for s in seams): warnings.append('Possible abrupt transition seam; listen at listed timestamps')
    if rms < .005: warnings.append('Low overall RMS level')
    return {'sample_rate':sr,'channels':channels,'duration_seconds':round(total_frames/sr,3),
            'peak_dbfs':db(peak),'rms_dbfs':db(rms),
            'samples_near_clipping':near_clipping,
            'quiet_window_fraction':round(silence,4),'seam_jumps':seams,
            'warnings':warnings,
            'note':'Sample checks only; no intersample true-peak, LUFS or perceptual scoring'}


def inspect(path, output=None):
    result = assess(path)
    if output:
        Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
