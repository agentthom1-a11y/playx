"""Private-by-default, loopback-only PlayX Studio and durable local render jobs.

This is a local desktop web UI. It is NOT an Internet-facing multi-tenant API.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .core import analyze, plan, render

VERSION = '0.3.0b1'
MAX_UPLOAD = 250 * 1024 * 1024
MAX_ACTIVE = 3
ALLOWED = {'.wav', '.flac', '.ogg', '.aif', '.aiff', '.mp3'}
executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='playx-render')
mutex = threading.RLock()
active_jobs: dict[str, dict] = {}


def workspace():
    return Path(os.environ.get('PLAYX_DATA_DIR', str(Path.home() / 'PlayX'))).expanduser().resolve()


def _safe_id(value):
    if not re.fullmatch(r'[0-9a-f]{32}', value):
        raise HTTPException(status_code=404, detail='Not found')
    return value


def _folder(kind, ident):
    return workspace() / kind / _safe_id(ident)


def _metadata(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path.with_name(path.name + '.tmp')
    target.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(target, path)


def _view_job(job):
    return {k: v for k,v in job.items() if k in ('id','state','stage','created_at','updated_at','result','error')}


def _job(ident):
    _safe_id(ident)
    with mutex:
        if ident in active_jobs: return active_jobs[ident].copy()
    path = _folder('jobs', ident) / 'job.json'
    if not path.is_file(): raise HTTPException(404, 'Unknown job')
    data = json.loads(path.read_text(encoding='utf-8'))
    if data['state'] in ('queued','running'):
        data['state'] = 'failed'
        data['error'] = 'Studio was restarted during this render; submit the job again.'
        _metadata(path, data)
    return data


def _update(ident, **values):
    with mutex:
        job = active_jobs[ident]
        job.update(values)
        job['updated_at'] = time.time()
        _metadata(_folder('jobs', ident) / 'job.json', job)


def _source(ident):
    folder = _folder('uploads', ident)
    path = folder / 'meta.json'
    if not path.is_file(): raise HTTPException(404, 'Upload not found')
    info = json.loads(path.read_text(encoding='utf-8'))
    filename = info.get('stored')
    if not filename or not re.fullmatch(r'input\.[a-z0-9]+', filename):
        raise HTTPException(400, 'Corrupt upload metadata')
    audio = folder / filename
    if not audio.is_file(): raise HTTPException(404, 'Uploaded audio not available')
    return audio


def _waveform(audio, bins=140):
    """Small normalized peak summary, read in bounded chunks; avoids client audio decoding."""
    with sf.SoundFile(audio) as source:
        duration = len(source) / source.samplerate
        if duration < 2 or duration > 12 * 60:
            raise ValueError('Track duration must be between 2 seconds and 12 minutes')
        block = max(1, (len(source)+bins-1)//bins)
        values = []
        for chunk in source.blocks(blocksize=block, dtype='float32', always_2d=True):
            values.append(round(float(np.max(np.abs(chunk))),3))
    ceiling = max(values, default=1.) or 1.
    return {'duration_seconds': round(duration,2), 'waveform': [round(v/ceiling,3) for v in values]}


class RenderRequest(BaseModel):
    a: str
    b: str
    style: str = 'auto'
    energy: float = Field(.7, ge=0, le=1)
    bars: int = Field(8)
    tempo_sync: bool = True


def _run(ident, request):
    try:
        _update(ident, state='running', stage='Analyzing deck A')
        a = analyze(str(_source(request.a)))
        _update(ident, stage='Analyzing deck B')
        b = analyze(str(_source(request.b)))
        _update(ident, stage='Planning transition')
        transition = plan(a, b, request.style, request.energy, request.bars, request.tempo_sync)
        _update(ident, stage='Rendering & checking audio')
        folder = _folder('jobs', ident)
        output = folder / 'playx-mix.wav'
        result = render(a.path, b.path, transition, str(output))
        _update(ident, state='done', stage='Complete', result={
            'plan': asdict(transition),
            'tracks': [{'duration': a.duration, 'bpm': a.bpm, 'key': a.key},
                       {'duration': b.duration, 'bpm': b.bpm, 'key': b.key}],
            'duration': result['duration'], 'quality': result['quality'],
            'audio_url': f'/api/jobs/{ident}/audio',
            'quality_url': f'/api/jobs/{ident}/quality',
        })
    except Exception as error:
        _update(ident, state='failed', stage='Failed', error=f'{type(error).__name__}: {str(error)[:240]}')


app = FastAPI(title='PlayX Studio', version=VERSION, docs_url=None, redoc_url=None)


@app.middleware('http')
async def protect_local_access(request: Request, call_next):
    try:
        host = urlparse('http://' + request.headers.get('host','')).hostname
    except ValueError:
        return JSONResponse({'detail':'Invalid host'},status_code=403)
    # Do not trust arbitrary Host headers (DNS rebinding); no public listener by default.
    if host not in ('localhost', '127.0.0.1', '[::1]', 'testserver'):
        return JSONResponse({'detail':'Local access only'}, status_code=403)
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin = request.headers.get('origin')
        if origin:
            parsed = urlparse(origin)
            try:
                trusted = parsed.scheme == 'http' and parsed.hostname in ('localhost','127.0.0.1','::1') and parsed.port in (None,8765)
            except ValueError:
                trusted = False
            if not trusted:
                return JSONResponse({'detail':'Cross-origin writes blocked'}, status_code=403)
    return await call_next(request)


@app.get('/', response_class=HTMLResponse)
def home():
    return (Path(__file__).parent / 'assets' / 'index.html').read_text(encoding='utf-8')


@app.get('/api/health')
def health():
    return {'version': VERSION, 'mode':'local-first', 'uploads_max_mib': MAX_UPLOAD // 1024 // 1024,
            'remote_storage':False, 'ai_required':False, 'beta':True}


@app.post('/api/uploads', status_code=201)
async def upload(file: UploadFile = File(...)):
    name = Path(file.filename or '').name
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED: raise HTTPException(415, 'Use WAV, FLAC, MP3, OGG or AIFF')
    ident = uuid4().hex
    folder = _folder('uploads', ident)
    folder.mkdir(parents=True,exist_ok=True)
    target = folder / f'input{ext}'
    total = 0
    try:
        with target.open('wb') as sink:
            while True:
                block = await file.read(1024 * 1024)
                if not block: break
                total += len(block)
                if total > MAX_UPLOAD:raise HTTPException(413, 'Audio exceeds 250 MiB limit')
                sink.write(block)
        if total == 0:raise HTTPException(400, 'Empty file')
        preview = await asyncio.get_running_loop().run_in_executor(executor, _waveform, target)
        metadata = {'id':ident, 'name':name[:150], 'stored':target.name, 'bytes':total, **preview}
        _metadata(folder / 'meta.json', metadata)
        return {k:v for k,v in metadata.items() if k!='stored'}
    except sf.LibsndfileError as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(415, 'Decoder cannot read this audio file; convert it to WAV/FLAC') from exc
    except ValueError as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(422, str(exc)) from exc
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    finally:
        await file.close()


@app.delete('/api/uploads/{ident}', status_code=204)
def delete_upload(ident: str):
    source = _folder('uploads', ident)
    if not source.is_dir():raise HTTPException(404, 'Upload not found')
    with mutex:
        for j in active_jobs.values():
            if j['state'] in ('queued','running') and ident in (j.get('a'),j.get('b')):
                raise HTTPException(409,'Cannot remove audio while render is active')
    shutil.rmtree(source)


@app.post('/api/jobs', status_code=202)
def create_job(payload: RenderRequest):
    if payload.a == payload.b: raise HTTPException(400, 'Choose two different audio files')
    _source(payload.a); _source(payload.b)
    if payload.bars not in (4,8,16,32): raise HTTPException(422, 'bars must be 4, 8, 16 or 32')
    if payload.style not in ('auto','smooth','bass_swap','filter_sweep','echo_out','drop_swap'):
        raise HTTPException(422,'Unknown transition style')
    with mutex:
        if sum(j['state'] in ('queued','running') for j in active_jobs.values()) >= MAX_ACTIVE:
            raise HTTPException(429, 'Render queue full; retry later')
        # Bound in-memory index; persisted jobs remain accessible through their IDs.
        for key in list(active_jobs):
            if len(active_jobs) < 100:break
            if active_jobs[key]['state'] in ('done','failed'):active_jobs.pop(key)
        ident = uuid4().hex
        job = {'id': ident, 'state':'queued','stage':'Queued','created_at':time.time(),
               'updated_at':time.time(), 'a':payload.a,'b':payload.b}
        active_jobs[ident] = job
        _metadata(_folder('jobs', ident) / 'job.json', job)
        executor.submit(_run,ident,payload)
    return _view_job(job)


@app.get('/api/jobs/{ident}')
def job_status(ident: str):
    return _view_job(_job(ident))


@app.get('/api/jobs/{ident}/audio')
def download_audio(ident: str):
    job = _job(ident)
    if job['state'] != 'done':raise HTTPException(409, 'Mix not ready')
    file = _folder('jobs', ident) / 'playx-mix.wav'
    if not file.is_file():raise HTTPException(404, 'Export missing')
    return FileResponse(file,media_type='audio/wav', filename=f'PlayX-{ident[:8]}.wav')


@app.get('/api/jobs/{ident}/quality')
def download_quality(ident: str):
    job = _job(ident)
    if job['state'] != 'done':raise HTTPException(409, 'Report not ready')
    file = _folder('jobs', ident) / 'playx-mix.wav.quality.json'
    if not file.is_file():raise HTTPException(404, 'Report missing')
    return FileResponse(file,media_type='application/json',filename=f'PlayX-{ident[:8]}-quality.json')


@app.post('/api/mix')
def legacy_mix(req: RenderRequest):
    raise HTTPException(400, 'Legacy path-based endpoint disabled. Upload both audio files and call /api/jobs.')
