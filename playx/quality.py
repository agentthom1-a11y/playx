"""Deterministic signal-level quality checks, not a subjective mixing score."""
from pathlib import Path
import json
import numpy as np
import soundfile as sf


def assess(path: str, seam_seconds=()):
    samples, sr = sf.read(path, dtype="float32", always_2d=True)
    if not len(samples):
        raise ValueError("Empty audio")
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples, dtype="float64"))))
    # Peak is sample peak, not intersample true-peak.
    db = lambda x: round(float(20 * np.log10(max(x, 1e-12))), 2)
    # Analyze silence in non-overlapping ~100 ms windows.
    win = max(1, sr // 10)
    mono = np.mean(np.square(samples[:len(samples)//win*win].astype("float64")), axis=1)
    energy = np.sqrt(np.mean(mono.reshape(-1, win), axis=1)) if len(mono) else np.array([])
    silence = float(np.mean(energy < 10 ** (-50 / 20))) if energy.size else 0.0
    jumps = []
    for second in seam_seconds:
        idx = round(second*sr)
        if 1 <= idx < len(samples):
            difference = float(np.max(np.abs(samples[idx] - samples[idx-1])))
            jumps.append({"at_seconds":round(float(second),3),"jump":round(difference,5)})
    warnings=[]
    if peak >= .999: warnings.append("Sample peaks at/near digital full scale")
    if silence > .35: warnings.append("Large fraction of audio is quiet (< -50 dBFS)")
    if any(s["jump"]>.7 for s in jumps): warnings.append("Possible abrupt transition seam; listen at listed timestamps")
    if rms < .005: warnings.append("Low overall RMS level")
    return {"sample_rate":sr,"duration_seconds":round(len(samples)/sr,3),
            "peak_dbfs":db(peak),"rms_dbfs":db(rms),
            "samples_near_clipping":int(np.count_nonzero(np.abs(samples)>=.999)),
            "quiet_window_fraction":round(silence,4),"seam_jumps":jumps,
            "warnings":warnings, "note":"Signal checks only; not a perceptual or loudness-normalization score"}


def inspect(path, output=None):
    result=assess(path)
    if output:
        Path(output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
