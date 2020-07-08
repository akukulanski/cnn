from nmigen import *
from cnn.rom import CircularROM
from cnn.stream_macc import MACC_AXIS
from cnn.interfaces import DataStream
from cnn.utils.operations import _incr

from math import log2, ceil


def accum_req_bits(w_a, w_b, n):
    # accum_req_bits = prod_req_bits + int(ceil(log2(test_size)))
    return w_a + w_b + int(ceil(log2(n)))


class mlpNode(Elaboratable):

    def __init__(self, data_w, weight_w, n_inputs, rom_init):
        assert len(rom_init) % (n_inputs+1) == 0
        accum_w = accum_req_bits(data_w, weight_w, n_inputs + 1) # +1 bias
        shift = weight_w - 1 # compensate weights gain

        self.n_inputs = n_inputs
        
        self.rom = CircularROM(width=weight_w,
                               init=rom_init)

        self.macc = MACC_AXIS(input_w=data_w,
                              coeff_w=weight_w,
                              accum_w=accum_w,
                              shift=shift)

        output_w = len(self.macc.output.data)
        assert output_w == accum_w - shift, (
            f'{output_w} == {accum_w} - {shift}')
        self.input = DataStream(width=data_w, direction='sink', name='input')
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
