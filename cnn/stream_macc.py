from nmigen import *
from cnn.interfaces import DataStream
from cnn.hdl_utils import Pipeline, signal_delay


class StreamMacc(Elaboratable):
    _doc_ = """
    Multiplier and accumulator with selectable output division to scale
    down result and a Stream interface.
    The main input data interface is a Stream interface, while
    for the coefficients a memory read port interface is used.
    While the memory has r_rdy==1, the dataflow control will be
    done in the input data stream interface. If the coefficients
    come from the same interface as the input data, just assign
    the ports of the Stream Macc you should just:
    * ignore r_en
    * tell the core that the memory is ready to be read when
      the input data is valid by assigning:
        core.r_rdy <-- core.input.valid

    Interfaces
    ----------
    input : Data Stream, input
        Input data.
        Each product between the input data and the coeff data
        will be accumulated, until a last is asserted. A last
        will flush the pipeline and output the valid result,
        clearing the accumulator afterwards.

    coeff : {r_data, r_en, r_rdy}, input
        Input coefficients.
        TO DO: Implement ReadportInterface

    output : Data Stream, output
        Output data. Will output valid data after a last is
        asserted in the input interface. Otherwise, it will
        keep accumulating.

    Parameters
    ----------
    width_i : int
        Bit width of data in stream interface.

    width_c : int
        Bit width of the coefficients.

    width_acc : int
        Bit width of the accumulator.

    shift : int
        The accumulator result will be shifted to the right by
        this number, so the output will be (accumulator / 2**shift).
    """

    def __init__(self, width_i, width_c, width_acc=None, shift=None):
        if width_acc is None:
            width_acc = 48
        if shift is None:
            shift = 0
        output_w = width_acc - shift
        self.shift = shift
        self.accumulator = Signal(signed(width_acc))
        self.input = DataStream(width=width_i, direction='sink', name='input')
        self.output = DataStream(width=output_w, direction='source', name='output')
        self.r_data = Signal(signed(width_c))
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
        
        accum_shifted = Signal(signed(self.output.width))

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
        out, = pipeline.add_stage( [_get_accum(self.accumulator) + m3] )
        pipeline.generate(m=m, ce=clken, domain='sync')

        comb += self.accumulator.eq(out)

        comb += accum_shifted.eq(out[self.shift:].as_signed())

        comb += self.output.data.eq(accum_shifted)
        comb += self.output.last.eq(self.output.valid)

        return m