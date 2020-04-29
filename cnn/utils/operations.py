from nmigen import *

def _incr(signal, modulo):
    if modulo == 2 ** len(signal):
        return signal + 1
    else:
        return Mux(signal == modulo - 1, 0, signal + 1)

def _and(signals):
    return Mux(Cat(*signals) == 2**len(signals)-1, 1, 0)


def _or(signals):
    return Mux(Cat(*signals) != 0, 1, 0)