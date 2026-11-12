"""PlayX command-line entrypoint; offline studio and experimental Mixxx live controls."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
import platform
import shutil
import sys
from .core import analyze, plan, render, save_json, load_plan


def main():
    p = argparse.ArgumentParser(prog='playx', description='Agentic DJ engine')
    sub = p.add_subparsers(dest='cmd', required=True)
    s=sub.add_parser('analyze');s.add_argument('track')
    for name in ('plan','render','mix'):
        s=sub.add_parser(name);s.add_argument('a');s.add_argument('b')
        s.add_argument('--out',default='plan.json' if name=='plan' else 'mix.wav')
        if name in ('plan','mix'):
            s.add_argument('--style',default='auto',choices=('auto','smooth','bass_swap','filter_sweep','echo_out','drop_swap'))
            s.add_argument('--energy',type=float,default=.7)
            s.add_argument('--bars',type=int,default=8,choices=(4,8,16,32))
            s.add_argument('--no-tempo-sync',action='store_true',help='Do not time-stretch incoming track')
        if name=='plan':s.add_argument('--ai',action='store_true')
        if name=='render':s.add_argument('--plan',required=True)
    s=sub.add_parser('quality');s.add_argument('track');s.add_argument('--out')
    sub.add_parser('studio')
    sub.add_parser('doctor')
    s=sub.add_parser('setmix');s.add_argument('tracks',nargs='+');s.add_argument('--out',required=True);s.add_argument('--bars',type=int,default=8,choices=(4,8,16,32));s.add_argument('--energy',type=float,default=.7);s.add_argument('--style',default='auto',choices=('auto','smooth','bass_swap','filter_sweep','echo_out','drop_swap'));s.add_argument('--no-tempo-sync',action='store_true')
    s=sub.add_parser('setlist');s.add_argument('music',nargs='+');s.add_argument('--limit',type=int,default=8);s.add_argument('--profile',choices=('wave','build','chill'),default='wave');s.add_argument('--out',default='setlist.json')

    sub.add_parser('mixxx-ports')
    s=sub.add_parser('mixxx-load-selected');s.add_argument('--port',required=True);s.add_argument('--deck',type=int,choices=(1,2),required=True)
    s=sub.add_parser('mixxx-load-next');s.add_argument('--port',required=True);s.add_argument('--deck',type=int,choices=(1,2),required=True)
    s=sub.add_parser('mixxx-status');s.add_argument('--port',required=True);s.add_argument('--input-port')
    s=sub.add_parser('mixxx-transition');s.add_argument('--port',required=True);s.add_argument('--seconds',type=float,default=8);s.add_argument('--style',choices=('smooth','bass_swap','filter_sweep','echo_out','drop_swap'),default='smooth');s.add_argument('--from-deck',type=int,choices=(1,2),default=1)
    s=sub.add_parser('mixxx-beatmix');s.add_argument('--port',required=True);s.add_argument('--input-port');s.add_argument('--bars',type=int,choices=(4,8,16,32),default=8);s.add_argument('--style',choices=('smooth','bass_swap','filter_sweep','echo_out','drop_swap'),default='smooth');s.add_argument('--from-deck',type=int,choices=(1,2),default=1);s.add_argument('--lead-beats',type=int,default=16);s.add_argument('--timeout',type=float,default=15)
    x=p.parse_args()
    if x.cmd=='studio':
        import uvicorn
        uvicorn.run('playx.studio:app',host='127.0.0.1',port=8765)
        return
    if x.cmd=='doctor':
        result={'python':sys.version.split()[0],'system':platform.platform(),
                'workspace':str(Path.home()/'PlayX'),'ffmpeg':shutil.which('ffmpeg'),
                'runtime':'Local render available; Mixxx needs installation and a MIDI port'}
        try:
            from .midi import ports
            result['midi_ports']=ports()
        except Exception as error:
            result['midi_error']=str(error)
    elif x.cmd=='setmix':
        from .setmix import mix_set
        result=mix_set(x.tracks,x.out,bars=x.bars,energy=x.energy,style=x.style,tempo_sync=not x.no_tempo_sync)
    elif x.cmd=='setlist':
        from .library import recommend
        result=recommend(x.music,x.limit,x.profile)
        target=Path(x.out)
        if target.exists():raise FileExistsError(f'Setlist exists: {target}')
        target.write_text(json.dumps(result,indent=2),encoding='utf-8')
        result={'output':str(target.resolve()),'tracks':len(result['tracks']),
                'skipped':result['skipped']}
    elif x.cmd=='quality':
        from .quality import inspect
        result=inspect(x.track,x.out)
    elif x.cmd.startswith('mixxx'):
        from .midi import ports,transition,beatmix,load_selected,load_next,deck_status
        if x.cmd=='mixxx-ports':result=ports()
        elif x.cmd=='mixxx-load-selected':result={'status':load_selected(x.port,x.deck)}
        elif x.cmd=='mixxx-load-next':result={'status':load_next(x.port,x.deck)}
        elif x.cmd=='mixxx-status':result={'loaded':deck_status(x.port,x.input_port)}
        elif x.cmd=='mixxx-transition':
            transition(x.port,x.seconds,x.style,x.from_deck)
            result={'status':'Completed wall-clock fade; not beat locked'}
        else:
            result=beatmix(x.port,x.bars,x.style,x.from_deck,x.timeout,x.lead_beats,x.input_port)
    elif x.cmd=='analyze':result=asdict(analyze(x.track))
    elif x.cmd=='render':result=render(x.a,x.b,load_plan(x.plan),x.out)
    else:
        a,b=analyze(x.a),analyze(x.b)
        proposal=plan(a,b,x.style,x.energy,x.bars,not x.no_tempo_sync)
        if getattr(x,'ai',False):
            from .agent import refine
            proposal=refine(a,b,proposal)
        if x.cmd=='plan':
            save_json(proposal,x.out)
            result=asdict(proposal)
        else:
            result=render(x.a,x.b,proposal,x.out)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
