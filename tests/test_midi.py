import sys
from types import SimpleNamespace
import pytest
from playx import midi


def test_load_selected_rejects_other_decks():
    with pytest.raises(ValueError):midi.load_selected('fake',3)


def test_beatmix_rejects_bad_parameters():
    with pytest.raises(ValueError):midi.beatmix('fake',bars=5)
    with pytest.raises(ValueError):midi.beatmix('fake',bars=8,from_deck=3)
    with pytest.raises(ValueError):midi.beatmix('fake',bars=8,timeout=0)


def test_beatmix_clock_and_status(monkeypatch):
    timeline={'now':0.0,'input_calls':0}
    sent=[]
    def message(kind,**kw):return SimpleNamespace(type=kind,**kw)
    class Input:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def iter_pending(self):
            timeline['input_calls']+=1
            if timeline['input_calls']==1:
                return [message('control_change',control=72,value=127),message('control_change',control=73,value=127)]
            return [message('control_change',control=70,value=127)]
    class Output:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def send(self,msg):sent.append(msg)
    monkeypatch.setitem(sys.modules,'mido',SimpleNamespace(Message=message,open_input=lambda _:Input(),open_output=lambda _:Output()))
    monkeypatch.setattr(midi.time,'monotonic',lambda:timeline['now'])
    monkeypatch.setattr(midi.time,'sleep',lambda sec:timeline.__setitem__('now',timeline['now']+.5))
    result=midi.beatmix('Fake',bars=4,lead_beats=1,timeout=15)
    assert result['beat_locked'] is True
    assert any(m.type=='note_on' and m.note==22 for m in sent)
    assert any(m.type=='control_change' and m.control==16 and m.value==127 for m in sent)
