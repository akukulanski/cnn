from nmigen import *
from cnn.rom import CircularROM
from cnn.stream_macc import StreamMacc
from cnn.interfaces import DataStream
from cnn.utils.operations import _incr

from math import log2, ceil


def accum_req_bits(w_a, w_b, n):
    return w_a + w_b + int(ceil(log2(n)))


class mlpNode(Elaboratable):
    _doc_ = """
    MLP Node instantiates a Stream Macc and a Circular ROM
    to store the corresponding weights. Both input and output
    are Stream interfaces.
    This MLP Node can actually do the job of N neurons serially
    where each neuron will require (n_inputs + 1) weights stored.

    Parameters
    ----------
    width_i : int
        Bit width of data in stream interface.

    width_w : int
        Bit width of data in the ROM.

    n_inputs : int
        Number of inputs for each neuron.

    rom_init : list
        List with weights to initialize the ROM. It should
        have the form
        [N0_W0, N0_W1, ..., N0_Wn-1, N0_Wbias,
         N1_W0, N1_W1, ..., N1_Wn-1, N1_Wbias,
         ...
        ]
        where Nx_Wy refers to the weight of the sample 'y'
        of neuron 'x'.
    """

    def __init__(self, width_i, width_w, n_inputs, rom_init):
        assert len(rom_init) % (n_inputs+1) == 0
        accum_w = accum_req_bits(width_i, width_w, n_inputs + 1) # +1 bias
        shift = width_w - 1 # compensate weights gain

        self.n_inputs = n_inputs
        
        self.rom = CircularROM(width=width_w,
                               init=rom_init)

        self.macc = StreamMacc(width_i=width_i,
                               width_c=width_w,
                               width_acc=accum_w,
                               shift=shift)

        output_w = len(self.macc.output.data)
        assert output_w == accum_w - shift, (
            f'{output_w} == {accum_w} - {shift}')
        self.input = DataStream(width=width_i, direction='sink', name='input')
        self.output = DataStream(width=output_w, direction='source', name='output')

    def get_ports(self):
        ports = []
        ports += [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        m.submodules.rom = rom = self.rom
        m.submodules.macc = macc = self.macc

        cnt = Signal(range(self.n_inputs))
        output_data = Signal(signed(len(self.output.data)))

        comb += macc.r_data.eq(rom.r_data)
        comb += macc.r_rdy.eq(rom.r_rdy)
        comb += rom.r_en.eq(macc.r_en)
        comb += rom.restart.eq(0) # should be unnecessary if the
                                  # inputs are correct.

        nxt_cnt = Signal.like(cnt)
        comb += nxt_cnt.eq(_incr(cnt, self.n_inputs))
        with m.If(self.input.accepted()):
            sync += cnt.eq(nxt_cnt)

        with m.FSM() as fsm:

            with m.State("INPUT"):
                comb += self.input.ready.eq(macc.input.ready)
                comb += macc.input.valid.eq(self.input.valid)
                comb += macc.input.data.eq(self.input.data)
                comb += macc.input.last.eq(0)
                with m.If(macc.input.accepted() & (nxt_cnt == 0)):
                    m.next = "BIAS"

            with m.State("BIAS"):
                comb += self.input.ready.eq(0)
                comb += macc.input.valid.eq(1)
                comb += macc.input.data.eq(1) # should it be bigger? what granularity should the bias have?
                comb += macc.input.last.eq(1)
                with m.If(macc.input.accepted()):
                    m.next = "INPUT"

        comb += output_data.eq(macc.output.data)
        comb += self.output.valid.eq(macc.output.valid)
        comb += self.output.data.eq(output_data)
        comb += self.output.last.eq(0) # self.input.last + delay?
        comb += macc.output.ready.eq(self.output.ready)

        return m
