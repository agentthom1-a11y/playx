"""Mixxx MIDI transport. Requires an installed, configured virtual MIDI port."""
from __future__ import annotations
import math
import time

STYLES = ('smooth', 'bass_swap', 'filter_sweep', 'echo_out', 'drop_swap')


def ports():
    import mido
    return {'input': mido.get_input_names(), 'output': mido.get_output_names()}


def envelope(style: str, fraction: float) -> float:
    """Normalized crossfader envelope in [0,1]; discrete beat-safe curves."""
    if style not in STYLES:
        raise ValueError(f'Unknown transition style: {style}')
    x = min(1.0, max(0.0, fraction))
    if style == 'drop_swap':
        return float(x >= .5)
    if style == 'echo_out':
        return min(1.0, max(0.0, (x-.65)/.35))
    if style == 'bass_swap':
        return min(1.0, max(0.0, (x-.25)/.5))
    if style == 'filter_sweep':
        return x*x*(3-2*x)
    return x


def send_cc(output, number, fraction):
    import mido
    output.send(mido.Message('control_change',channel=0,control=number,
                             value=round(127*min(1.0,max(0.0,fraction)))))


def send_action(output, number):
    import mido
    output.send(mido.Message('note_on',channel=0,note=number,velocity=127))
    output.send(mido.Message('note_off',channel=0,note=number,velocity=0))


def load_selected(port: str, deck: int):
    """Load highlighted Mixxx library row, never a guessed path."""
    if deck not in (1,2): raise ValueError('deck must be 1 or 2')
    import mido
    with mido.open_output(port) as output:
        send_action(output, 20 if deck == 1 else 21)
    return 'LoadSelectedTrack command sent (requires highlighted row in Mixxx)'


def load_next(port: str, deck: int, settle_seconds: float = 0.25):
    """Advance library selection then load it; Mixxx window/library must be focused."""
    if deck not in (1,2): raise ValueError('deck must be 1 or 2')
    import mido
    with mido.open_output(port) as output:
        send_action(output, 29)
        time.sleep(settle_seconds)
        send_action(output, 20 if deck == 1 else 21)
    return 'MoveDown + LoadSelectedTrack sent; verify Mixxx highlighted row and deck'


def deck_status(port: str, input_port: str | None = None, timeout: float = 2.5):
    """Query loaded flags; returns only what Mixxx actually acknowledged."""
    import mido
    flags={}
    with mido.open_input(input_port or port) as incoming, mido.open_output(port) as output:
        send_action(output,30)
        deadline=time.monotonic()+timeout
        while len(flags)<2 and time.monotonic()<deadline:
            for msg in incoming.iter_pending():
                if msg.type=='control_change' and msg.control in (72,73):
                    flags[1 if msg.control==72 else 2]=bool(msg.value)
            if len(flags)<2: time.sleep(.02)
    if len(flags)<2: raise TimeoutError('No deck status response from Mixxx: check mapping and virtual MIDI ports')
    return flags


def transition(port: str, seconds: float, style='smooth', from_deck=1, tick=.025):
    """Wall-clock fallback: no feedback or beat locking. Use beatmix where possible."""
    if not 0 < seconds <= 600: raise ValueError('seconds must be 0..600')
    if from_deck not in (1,2): raise ValueError('from_deck must be 1 or 2')
    import mido
    with mido.open_output(port) as output:
        start=time.monotonic()
        while True:
            elapsed=time.monotonic()-start
            x=envelope(style,elapsed/seconds)
            send_cc(output,16,x if from_deck == 1 else 1-x)
            if elapsed >= seconds: break
            time.sleep(tick)


def beatmix(port: str, bars: int = 8, style: str='smooth', from_deck: int = 1,
            timeout: float = 15.0, lead_beats: int = 16, input_port: str | None = None):
    """Mixxx beat-active feedback drives the timeline. Fails closed without feedback.

    Assumptions: A is playing and routed left/right to the crossfader,
    B is preloaded, and Mixxx's beatgrid is correct. The callback reports
    each A deck beat over MIDI CC70 (or CC71 for deck 2).
    """
    if bars not in (4,8,16,32): raise ValueError('bars must be 4, 8, 16 or 32')
    if style not in STYLES: raise ValueError('Unknown style')
    if from_deck not in (1,2): raise ValueError('from_deck must be 1 or 2')
    if timeout <= 0: raise ValueError('timeout must be positive')
    if lead_beats < 1 or lead_beats > 256: raise ValueError('lead_beats must be 1..256')
    import mido
    source = input_port or port
    beat_cc=70 if from_deck == 1 else 71
    # A rolling estimate for smooth parameter changes between MIDI beat events.
    times=[]; last_beat=None; deadline=time.monotonic()+timeout
    started=False; beat_index=0; total=bars*4
    with mido.open_input(source) as incoming, mido.open_output(port) as output:
        loaded={}
        send_action(output,30)
        status_deadline=time.monotonic()+min(timeout,2.5)
        while len(loaded)<2 and time.monotonic()<status_deadline:
            for msg in incoming.iter_pending():
                if msg.type=='control_change' and msg.control in (72,73):
                    loaded[1 if msg.control==72 else 2]=bool(msg.value)
            if len(loaded)<2:time.sleep(.02)
        if len(loaded)<2:raise TimeoutError('No loaded-deck status from Mixxx')
        if not all(loaded.values()):raise ValueError('Both decks must have tracks loaded before beatmix')
        send_cc(output,16,0 if from_deck == 1 else 1)
        while True:
            now=time.monotonic()
            for msg in incoming.iter_pending():
                if msg.type != 'control_change' or msg.control != beat_cc or msg.value != 127:
                    continue
                if last_beat is not None and now-last_beat < .16:
                    continue  # suppress duplicate feedback and fractional-loop bursts
                if last_beat is not None and .16 <= now-last_beat <= 2.5:
                    times.append(now-last_beat)
                    times=times[-8:]
                last_beat=now
                if not started:
                    beat_index += 1
                    if beat_index == lead_beats:
                        # Set Mixxx deck 2/1 keylock + sync and start the deck at the beat.
                        send_action(output, 24 if from_deck == 1 else 25)
                        send_action(output, 22 if from_deck == 1 else 23)
                        started=True
                        beat_index=0
                else:
                    beat_index += 1
            if started:
                period=sorted(times)[len(times)//2] if times else .5
                fraction=min(1.0, (beat_index + min(1.0,(now-last_beat)/period))/total)
                x=envelope(style,fraction)
                send_cc(output,16,x if from_deck == 1 else 1-x)
                if fraction>=1.0:
                    send_cc(output,16,1 if from_deck == 1 else 0)
                    return {'bars':bars,'style':style,'feedback_beats':beat_index,'beat_locked':True}
            if not started and now >= deadline:
                raise TimeoutError('No beat feedback from Mixxx; check PlayX mapping, input port and deck playback')
            if started and last_beat is not None and now-last_beat > max(3.0,3*(sorted(times)[len(times)//2] if times else .5)):
                raise TimeoutError('Lost Mixxx beat feedback; leaving crossfader at last position')
            time.sleep(.02)
