"""Experimental multi-track DJ set renderer.

Uses existing two-deck engine in sequence. Intermediate generations are 24-bit WAV;
future releases should replace this with a single-pass streaming signal graph.
"""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
import tempfile

import soundfile as sf

from .core import Track, analyze, plan, render


def mix_set(paths, out, *, bars=8, energy=.7, style='auto', tempo_sync=True):
    if not 2 <= len(paths) <= 6:
        raise ValueError('Beta setmix supports 2 to 6 input tracks')
    target=Path(out).expanduser().resolve()
    if target.exists():raise FileExistsError(f'Output already exists: {target}')
    if target.suffix.lower() != '.wav':raise ValueError('Set output must be WAV')
    # Analyze all before creating any output; avoids partially finished projects.
    tracks=[analyze(p) for p in paths]
    target.parent.mkdir(parents=True,exist_ok=True)
    steps=[]
    with tempfile.TemporaryDirectory(prefix='playx-set-') as folder:
        current_path=tracks[0].path
        current_track=tracks[0]
        for index,next_track in enumerate(tracks[1:],start=1):
            step=plan(current_track,next_track,style,energy,bars,tempo_sync)
            final=index==len(tracks)-1
            dest=str(target if final else Path(folder)/f'part-{index}.wav')
            result=render(current_path,next_track.path,step,dest)
            new_duration=sf.info(dest).duration
            # Convert the incoming song's beat positions to the accumulated timeline.
            # This tracks phrase phase through the previous tempo stretch, rather
            # than pretending the entire mix is a fresh single-track beatgrid.
            rate=step.tempo_ratio if step.tempo_sync else 1.0
            beats=[round(step.start_a+(b-step.start_b)/rate,3)
                   for b in next_track.beats if b>=step.start_b]
            effective_bpm=current_track.bpm if step.tempo_sync else next_track.bpm
            current_track=Track(dest,new_duration,effective_bpm,next_track.key,beats,next_track.energy)
            current_path=dest
            steps.append({'from':index,'to':index+1,'plan':asdict(step),
                          'export_duration_seconds':round(new_duration,2)})
    manifest={'version':1,'track_count':len(tracks),'tracks':[{'name':Path(t.path).name,'bpm':t.bpm,'key':t.key,'duration':t.duration} for t in tracks],
              'transitions':steps,'quality':result['quality'],
              'warning':'Multi-pass mixing is experimental; 24-bit intermediate exports can accumulate processing artifacts.'}
    Path(str(target)+'.set.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return {'output':str(target),'duration_seconds':round(sf.info(target).duration,2),
            'track_count':len(tracks),'manifest':str(target)+'.set.json','quality':result['quality']}
