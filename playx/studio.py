"""Loopback-only studio; explicit local paths, no arbitrary remote uploads."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .core import analyze, plan, render

app=FastAPI(title='PlayX Studio',version='0.2.0')
executor=ThreadPoolExecutor(max_workers=1)
class MixRequest(BaseModel):
    a: str
    b: str
    out: str = 'mix.wav'
    style: str = 'auto'
    energy: float = Field(default=.7,ge=0,le=1)
    bars: int = Field(default=8,ge=4,le=32)
    tempo_sync: bool = True

@app.get('/',response_class=HTMLResponse)
def home():
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PlayX / Studio</title>
<style>:root{font-family:Inter,system-ui,sans-serif;color:#eee;background:#0b0b0e}body{margin:0}main{max-width:880px;margin:6vh auto;padding:26px}header{display:flex;align-items:center;justify-content:space-between}small,.muted{color:#999}h1{font-size:clamp(44px,8vw,84px);letter-spacing:-.07em;margin:35px 0 4px}p{color:#a8a8ad}.panel{background:#151519;border:1px solid #29292f;border-radius:20px;padding:24px;margin-top:30px}label{display:block;color:#bbb;margin:17px 0 8px;font-size:13px}input,select{box-sizing:border-box;width:100%;background:#0d0d11;color:#f4f4f4;border:1px solid #37373f;border-radius:10px;padding:13px;font-size:15px}button{border:0;border-radius:12px;background:#d5bb83;color:#111;padding:15px 24px;font-weight:700;cursor:pointer;margin-top:24px;width:100%}button:disabled{opacity:.5;cursor:wait}.row{display:grid;grid-template-columns:1fr 1fr;gap:15px}pre{white-space:pre-wrap;word-break:break-word;color:#c4d8cb;font-size:13px} .tag{border:1px solid #6d5e42;color:#d5bb83;border-radius:20px;padding:8px 12px;font-size:12px}@media(max-width:620px){.row{grid-template-columns:1fr}}</style>
<main><header><strong>PLAYX <span style="color:#d5bb83">/</span> LAB</strong><span class="tag">LOCAL FIRST · v0.2</span></header><h1>Mix beyond<br><span style="color:#d5bb83">the algorithm.</span></h1><p>Agentic DJ planning and deterministic audio rendering. Two tracks, one intentional transition.</p><section class="panel"><form id="mix"><label>DECK A · ABSOLUTE FILE PATH</label><input name="a" required placeholder="C:\\Music\\first.wav"><label>DECK B · ABSOLUTE FILE PATH</label><input name="b" required placeholder="C:\\Music\\second.wav"><label>OUTPUT WAV</label><input name="out" value="mix.wav" required><div class="row"><div><label>TRANSITION</label><select name="style"><option>auto</option><option>smooth</option><option>bass_swap</option><option>filter_sweep</option><option>echo_out</option><option>drop_swap</option></select></div><div><label>ENERGY · 0–1</label><input name="energy" type="number" min="0" max="1" step="0.1" value="0.7"></div></div><label><input name="tempo_sync" type="checkbox" checked style="width:auto"> Tempo sync (pitch preserving; slower)</label><label>PHRASE LENGTH · BARS</label><select name="bars"><option>4</option><option selected>8</option><option>16</option><option>32</option></select><button id="go">Analyze → Plan → Render</button></form><pre id="status" role="status">Ready. Local audio is not uploaded to an external server.</pre></section><p class="muted"><small>Preview and verify beat grid, musical key and loudness before publishing. Only use tracks you have permission to mix.</small></p></main><script>document.querySelector('#mix').onsubmit=async(e)=>{e.preventDefault();const btn=document.querySelector('#go'),status=document.querySelector('#status');btn.disabled=true;status.textContent='Analyzing and rendering… this may take a few minutes.';const d=Object.fromEntries(new FormData(e.target));d.energy=Number(d.energy);d.bars=Number(d.bars);d.tempo_sync=!!document.querySelector('input[name="tempo_sync"]').checked;try{const r=await fetch('/api/mix',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});const x=await r.json();status.textContent=JSON.stringify(x,null,2);if(!r.ok)status.textContent='Error: '+status.textContent;}catch(err){status.textContent=String(err)}finally{btn.disabled=false}};</script></html>'''

def do_mix(req):
    a=analyze(req.a);b=analyze(req.b)
    p=plan(a,b,req.style,req.energy,req.bars,req.tempo_sync)
    return {'track_a':asdict(a),'track_b':asdict(b),'plan':asdict(p),'render':render(req.a,req.b,p,req.out)}

@app.post('/api/mix')
async def mix(req:MixRequest):
    import asyncio
    try: return await asyncio.get_running_loop().run_in_executor(executor,do_mix,req)
    except (OSError,ValueError,RuntimeError) as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
