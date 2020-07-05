from nmigen import *
from cnn.interfaces import DataStream
from cnn.hdl_utils import Pipeline, signal_delay


class MACC_AXIS(Elaboratable):

    output_w = 48

    def __init__(self, input_w, coeff_w):
        self.input = DataStream(width=input_w, direction='sink', name='input')
        self.output = DataStream(width=self.output_w, direction='source', name='output')
        self.r_data = Signal(signed(coeff_w))
        self.r_en = Signal()
        self.r_rdy = Signal()
        self.latency = 5

    def get_ports(self):
        ports = [self.r_data, self.r_en, self.r_rdy]
        ports += [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        sync = m.d.sync

        clken = Signal()
        accepted_last = self.input.accepted() & self.input.last
        last_delayed = signal_delay(m, accepted_last, self.latency, ce=clken)
        
        _acc = Signal(signed(48))

        comb += self.output.last.eq(self.output.valid)
        comb += self.output.data.eq(_acc)

        with m.FSM() as fsm:

            with m.State("ACCUM"):
                comb += self.input.ready.eq(self.r_rdy)
                comb += self.output.valid.eq(0)
                comb += self.r_en.eq(self.input.accepted())
                comb += clken.eq(self.input.accepted())
                with m.If(self.input.accepted() & self.input.last):
                    m.next = "LAST"
            with m.State("LAST"):
                comb += self.input.ready.eq(0)
                comb += self.output.valid.eq(last_delayed)
                comb += self.r_en.eq(0)
                comb += clken.eq(~self.output.valid | self.output.accepted())
                with m.If(self.output.accepted()):
                    m.next = "ACCUM"

        _get_input = lambda x: Mux(self.input.accepted(), x, 0)
        _get_accum = lambda x: Mux(self.output.accepted(), 0, x)

        pipeline = Pipeline()
        a0, b0 = pipeline.add_stage( [_get_input(self.input.data.as_signed()),
                                      _get_input(self.r_data.as_signed())] )
        a1, b1 = pipeline.add_stage( [a0, b0] )
        m2, = pipeline.add_stage( [a1 * b1] )
        m3, = pipeline.add_stage( [m2] )
        out, = pipeline.add_stage( [_get_accum(_acc) + m3] )
        pipeline.generate(m=m, ce=clken, domain='sync')

        comb += _acc.eq(out)
        comb += self.output.data.eq(out)

        return m