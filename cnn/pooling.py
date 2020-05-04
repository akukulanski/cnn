from nmigen import *
from cnn.interfaces import DataStream
from cnn.matrix_feeder import MatrixFeeder
from cnn.utils.operations import _incr

class MatrixFeederSkip(MatrixFeeder):
    
    def __init__(self, *args, **kwargs):
        MatrixFeeder.__init__(self, *args, **kwargs)
        assert self.row_length % self.N == 0, (
            f'image_w must be a multiple of N. Psss, you can use Padder() to append zeros!')

    def elaborate(self, platform):
        m = MatrixFeeder.elaborate(self, platform)
        sync = m.d.sync
        comb = m.d.comb

        submatrix = m.submodules.submatrix_regs
        alt_ready = Signal() # ready for the 
        pooling_counter = Signal(range(self.N))

        with m.If(submatrix.output.accepted()):
            sync += pooling_counter.eq(_incr(pooling_counter))
            # sync += pooling_counter.eq(Mux(submatrix.output.last, 0, _incr(pooling_counter)))

        # now the output handshake (valid/ready/last) is not connected directly to "submatrix"
        # matrix feeder --> output
        with m.If(pooling_counter == 0):
            comb += [self.output.valid.eq(submatrix.output.valid),
                     self.output.last.eq(submatrix.output.last), # PROBLEM HERE!
                     submatrix.output.ready.eq(self.output.ready),
                    ]
        with m.Else():
            comb += [self.output.valid.eq(0),
                     self.output.last.eq(0),
                     matrix_feeder.output.ready.eq(1),
                    ]

        return m


class Pooling(Elaboratable):
    
    def __init__(self, width, image_w, N):
        assert image_w % N == 0, (
            f'image_w must be a multiple of N. Psss, you can use Padder() to append zeros!')
        self.image_w = image_w
        self.matrix_feeder = MatrixFeederSkip(input_w=width,
                                              row_length=image_w,
                                              N=N)
        self.input = DataStream(width=width, direction='sink', name='input')
        self.output = DataStream(width=width, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    @property
    def N(self):
        return self.matrix_feeder.shape[0]

    @property
    def image_w_o(self):
        return int(self.image_w // self.N)

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        assert False, 'Not implemented'

        return m

