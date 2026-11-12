from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import asyncio
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from .core import analyze,plan,render

app=FastAPI(title="PlayX Studio",version="0.1.0")
pool=ThreadPoolExecutor(max_workers=1)
class MixRequest(BaseModel):
    a:str
    b:str
    out:str="mix.wav"
    style:str="auto"
    energy:float=Field(default=.7,ge=0,le=1)
    bars:int=8

HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PlayX Studio</title>
<style>body{background:#0b0b0e;color:#eee;font:16px system-ui;margin:0}main{max-width:800px;margin:5vh auto;padding:24px}h1{font-size:clamp(50px,8vw,90px);letter-spacing:-.07em;margin:35px 0 10px}em{color:#d5bb83;font-style:normal}p{color:#aaa}.panel{background:#17171b;border:1px solid #333;border-radius:20px;padding:24px}label{display:block;margin:18px 0 8px;color:#aaa;font-size:12px}input,select{box-sizing:border-box;width:100%;background:#0e0e11;color:white;border:1px solid #444;border-radius:10px;padding:13px;font-size:15px}button{background:#d5bb83;border:0;border-radius:12px;padding:15px;font-weight:bold;width:100%;margin-top:24px;cursor:pointer}button:disabled{opacity:.5}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#c4d8cb}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:600px){.row{grid-template-columns:1fr}}</style>
<main><b>PLAYX / LAB</b><h1>Mix beyond<br><em>the algorithm.</em></h1><p>Local-first agentic DJ planning and deterministic audio rendering.</p><div class="panel"><form id="f"><label>DECK A · ABSOLUTE PATH</label><input name="a" required placeholder="C:\\Music\\first.wav"><label>DECK B · ABSOLUTE PATH</label><input name="b" required placeholder="C:\\Music\\second.wav"><label>OUTPUT WAV</label><input name="out" value="mix.wav"><div class="row"><div><label>STYLE</label><select name="style"><option>auto</option><option>smooth</option><option>bass_swap</option><option>filter_sweep</option><option>echo_out</option><option>drop_swap</option></select></div><div><label>ENERGY 0–1</label><input name="energy" type="number" min="0" max="1" step=".1" value=".7"></div></div><label>BARS</label><select name="bars"><option>4</option><option selected>8</option><option>16</option><option>32</option></select><button id="go">Analyze → Plan → Render</button></form><pre id="status">Ready. Audio stays on your machine.</pre></div><p>Check BPM and beat alignment by ear. Use only music you are authorized to mix.</p></main>
<script>document.querySelector("#f").onsubmit=async e=>{e.preventDefault();const btn=document.querySelector("#go"),s=document.querySelector("#status");btn.disabled=true;s.textContent="Rendering…";const x=Object.fromEntries(new FormData(e.target));x.energy=Number(x.energy);x.bars=Number(x.bars);try{const r=await fetch("/api/mix",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(x)});s.textContent=JSON.stringify(await r.json(),null,2)}catch(err){s.textContent=String(err)}finally{btn.disabled=false}}</script></html>'''
@app.get("/",response_class=HTMLResponse)
def home():return HTML

def run(req):
    a,b=analyze(req.a),analyze(req.b)
    p=plan(a,b,req.style,req.energy,req.bars)
    return {"track_a":asdict(a),"track_b":asdict(b),"plan":asdict(p),"render":render(req.a,req.b,p,req.out)}

@app.post("/api/mix")
async def mix(req:MixRequest):
    try:return await asyncio.get_running_loop().run_in_executor(pool,run,req)
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
