from nmigen import *
from cnn.interfaces import DataStream


_lsb = 0
_msb = -1


def _signed_shift_right(signal, shift):
    return Cat(signal[shift:], Repl(signal[_msb], shift))


def _relu(signal, leak):
    assert leak >= 0 and leak <= len(signal)
    if leak == 0:
        leaked_value = 0
    else:
        shift = len(signal) - leak
        leaked_value = _signed_shift_right(signal, shift)
    return Mux(signal[_msb] == 0, signal, leaked_value)


class Relu(Elaboratable):
    _doc_ = """
    ReLu operation.

    Interfaces
    ----------
    input : Stream, input
        Data input.

    output : Stream, output
        Data output.

    Parameters
    ----------
    width : int
        Bit width of the data.

    leak : int
        leak of the ReLu function (in bits).
        The negative inputs will be shifted to
        the right by (width - leak)
        0 - all negative values converted to 0
        1 - all negative values converted to -1
        2 - all negative values between [-2, -1]
        3 - all negative values between [-4, -1]
        ...
        width-2 - all negative values divided by 4
        width-1 - all negative values divided by 2
        width - identity (output=input)

    """

    def __init__(self, width, leak=0):
        self.leak = leak
        self.input = DataStream(width=width, direction='sink', name='input')
        self.output = DataStream(width=width, direction='source', name='output')

    def get_ports(self):
        ports = []
        ports += [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        x = Signal()
        sync += x.eq(~x) # Lets force the existence of a clock in the design

        comb += [
            self.output.valid.eq(self.input.valid),
            self.output.data.eq(_relu(self.input.data, self.leak)),
            self.output.last.eq(self.input.last),
            self.input.ready.eq(self.output.ready),
        ]

        return m