import os,json
from dataclasses import asdict,replace

def refine(a,b,proposal):
    import anthropic
    if not os.getenv("ANTHROPIC_API_KEY") or not os.getenv("ANTHROPIC_MODEL"):
        raise RuntimeError("Set ANTHROPIC_API_KEY and ANTHROPIC_MODEL")
    client=anthropic.Anthropic()
    payload={"a":{k:v for k,v in asdict(a).items() if k not in ("path","beats")},"b":{k:v for k,v in asdict(b).items() if k not in ("path","beats")},"proposal":asdict(proposal)}
    response=client.messages.create(model=os.environ["ANTHROPIC_MODEL"],max_tokens=160,system='Return only JSON with keys "style" and "rationale". style must be one of smooth,bass_swap,filter_sweep,echo_out,drop_swap.',messages=[{"role":"user","content":json.dumps(payload)}])
    raw="".join(b.text for b in response.content if b.type=="text").strip()
    if raw.startswith("```"):raw=raw.split("\n",1)[1].rsplit("```",1)[0].strip()
    data=json.loads(raw)
    if data.get("style") not in ("smooth","bass_swap","filter_sweep","echo_out","drop_swap"):raise ValueError("invalid agent style")
    return replace(proposal,style=data["style"],rationale=str(data.get("rationale",""))[:300])
