import argparse, json
from dataclasses import asdict
from .core import analyze,plan,render,save_json,load_plan

def main():
    p=argparse.ArgumentParser(prog="playx")
    sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("analyze");s.add_argument("track")
    for name in ("plan","render","mix"):
        s=sub.add_parser(name);s.add_argument("a");s.add_argument("b")
        s.add_argument("--out",default="plan.json" if name=="plan" else "mix.wav")
        if name=="plan":
            s.add_argument("--style",default="auto");s.add_argument("--energy",type=float,default=.7)
            s.add_argument("--bars",type=int,default=8);s.add_argument("--ai",action="store_true")
        if name=="render":s.add_argument("--plan",required=True)
    sub.add_parser("studio");sub.add_parser("mixxx-ports")
    s=sub.add_parser("mixxx-transition");s.add_argument("--port",required=True);s.add_argument("--seconds",type=float,default=8)
    x=p.parse_args()
    if x.cmd=="studio":
        import uvicorn
        uvicorn.run("playx.studio:app",host="127.0.0.1",port=8765);return
    if x.cmd.startswith("mixxx"):
        from .midi import ports,transition
        if x.cmd=="mixxx-ports":print("\n".join(ports()));return
        transition(x.port,x.seconds);return
    if x.cmd=="analyze":result=asdict(analyze(x.track))
    elif x.cmd=="render":result=render(x.a,x.b,load_plan(x.plan),x.out)
    else:
        a,b=analyze(x.a),analyze(x.b)
        proposal=plan(a,b,getattr(x,"style","auto"),getattr(x,"energy",.7),getattr(x,"bars",8))
        if getattr(x,"ai",False):
            from .agent import refine
            proposal=refine(a,b,proposal)
        if x.cmd=="plan":save_json(proposal,x.out);result=asdict(proposal)
        else:result=render(x.a,x.b,proposal,x.out)
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
