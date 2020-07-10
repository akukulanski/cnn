from nmigen import *
from cnn.dot_product import DotProduct
from cnn.interfaces import MatrixStream, DataStream
from cnn.utils.operations import _incr


class Farm(Elaboratable):
    _doc_ = """
    "Farm" of DotProduct cores, for parallel computation.
    The performed operation is the dot product of two NxM
    matrixes.

    Keep in mind that since throughput will never be higher
    than one output per clock, it doesn't make sense to use
    a higher number of DotProduct cores than the latency of
    each one of them.

    The dataflow is controlled ONLY by the input_a Stream interface.
    The input_b stream interface is DUMMY, and should always
    have valid values in the input. The ready of the input_b
    interface will be attached to input_a.accepted(), and a valid=1
    will be assumed. Why?
    I want to avoid a combinational path between the valid of input_b
    and the ready of input_a.

    Interfaces
    ----------
    input_a : Matrix Stream, input
        Input a matrix data.

    input_b : Matrix Stream, input
        Input b matrix data.
        TO DO: should not be a stream, but plain "matrix shaped" values.

    output : Data Stream, output
        Dot product computated value.

    Parameters
    ----------
    width : int
        Bit width of both inputs.

    shape : tuple
        Input shape (N, M).

    n_cores : int
        Number of paralell computations of dot product.
    """

    def __init__(self, width, shape, n_cores):
        self.cores = [DotProduct(width, shape) for _ in range(n_cores)]
        self.input_a = MatrixStream(width=width, shape=shape, direction='sink', name='input_a')
        self.input_b = MatrixStream(width=width, shape=shape, direction='sink', name='input_b')
        self.output = DataStream(self.output_w, direction='source', name='output')

    def get_ports(self):
        ports = []
        ports += [self.input_a[f] for f in self.input_a.fields]
        ports += [self.input_b[f] for f in self.input_b.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    @property
    def input_w(self):
        return self.input_a.width
    
    @property
    def n_inputs(self):
        return self.input_a.n_elements

    @property
    def shape(self):
        return self.input_a.shape

    @property
    def output_w(self):
        return self.cores[0].output_w

    @property
    def n_cores(self):
        return len(self.cores)

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        current_core_sink = Signal(range(self.n_cores))
        current_core_source = Signal(range(self.n_cores))

        # DUMMY input_b interface
        # comb += [self.input_b.ready.eq(self.input_a.accepted())]

        for i, core in enumerate(self.cores):
            m.submodules['core_' + str(i)] = core
            comb += core.input_b.connect_data_ports(self.input_b) # same coefficients for everybody
            with m.If(current_core_sink == i):
                comb += [self.input_a.ready.eq(core.input_a.ready),
                         self.input_b.ready.eq(core.input_b.ready),
                        ]
                comb += [core.input_a.valid.eq(self.input_a.valid),
                         core.input_b.valid.eq(self.input_b.valid),
                         core.input_a.connect_data_ports(self.input_a),
                        ]
            with m.Else():
                comb += [core.input_a.valid.eq(0),
                         core.input_b.valid.eq(0),
                         core.input_a.connect_to_const(0),
                        ]
            with m.If(current_core_source == i):
                comb += [self.output.valid.eq(core.output.valid),
                         self.output.data.eq(core.output.data),
                        ]
                comb += [core.output.ready.eq(self.output.ready),
                        ]
            with m.Else():
                comb += [core.output.ready.eq(0),
                        ]

        with m.If(self.input_a.accepted()):
            sync += current_core_sink.eq(_incr(current_core_sink, self.n_cores))

        with m.If(self.output.accepted()):
            sync += current_core_source.eq(_incr(current_core_source, self.n_cores))

        return m
