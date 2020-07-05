from nmigen import *

class Pipeline():

    def __init__(self):
        self._stages = []
        self._signals = []

    def add_stage(self, stage_ops):
        s = len(self._stages)
        _signals = [Signal.like(op, name='s'+str(s)+'_'+str(i)) for i, op in enumerate(stage_ops)]
        self._stages.append(stage_ops)
        self._signals.append(_signals)
        return _signals

    def generate(self, m, ce, domain='sync'):
        with m.If(ce):
            for _signals, _stage_ops in zip(self._signals, self._stages):
                for sig, op in zip(_signals, _stage_ops):
                    m.d[domain] += sig.eq(op)

    @property
    def latency(self):
        return len(self._stages)


def signal_delay(m, signal, latency, ce=None, domain='sync'):
    if ce is None:
        ce = Const(1)
    shift_reg = Array([Signal.like(signal) for _ in range(latency)])
    m.d[domain] += shift_reg[0].eq(signal)
    with m.If(ce):
        for prv, nxt in zip(shift_reg[:-1], shift_reg[1:]):
            m.d[domain] += nxt.eq(prv)
    return shift_reg[-1]