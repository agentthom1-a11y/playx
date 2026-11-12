import time

def ports():
    import mido
    return mido.get_output_names()

def transition(port,seconds):
    import mido
    if not 0<seconds<=600:raise ValueError("seconds must be 0..600")
    with mido.open_output(port) as output:
        start=time.monotonic()
        while True:
            elapsed=time.monotonic()-start
            value=round(127*min(1,elapsed/seconds))
            output.send(mido.Message("control_change",channel=0,control=16,value=value))
            if elapsed>=seconds:break
            time.sleep(.025)
