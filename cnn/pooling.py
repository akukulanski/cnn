from nmigen import *
from cnn.interfaces import DataStream
from cnn.matrix_feeder import MatrixFeeder
from cnn.tree_operations_wrapped import TreeHighestUnsignedWrapped
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

    _modes = {
        'highest': TreeHighestUnsignedWrapped
    }
    
    def __init__(self, width, image_w, N, mode):
        assert image_w % N == 0, (
            f'image_w must be a multiple of N. Psss, you can use Padder() to append zeros!')
        assert mode in self._modes, 'Unsupported mode'
        self.mode = mode
        self.image_w = image_w
        self.matrix_feeder = MatrixFeederSkip(input_w=width,
                                              row_length=image_w,
                                              N=N,
                                              invert=False)
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

        pooling_core = self._modes[self.mode]

        n_inputs = self.matrix_feeder.N ** 2
        tree_n_stages = int(ceil(log2(n_inputs)))

        m.submodules.matrix_feeder = matrix_feeder = self.matrix_feeder
        m.submodules.pooler = pooler = pooling_core(input_w=self.width,
                                                    n_stages=tree_n_stages,
                                                    reg_in=False,
                                                    reg_out=False)

        tree_n_inputs = len(pooler.inputs)

        # input --> matrix_feeder
        comb += [
            matrix_feeder.input.valid.eq(self.input.valid),
            matrix_feeder.input.last.eq(self.input.last),
            matrix_feeder.input.data.eq(self.input.data),
            self.input.ready.eq(matrix_feeder.input.ready),
        ]

        # matrix_feeder --> pooler
        comb += [
            pooler.input.valid.eq(matrix_feeder.output.valid),
            pooler.input.last.eq(matrix_feeder.output.last),
            matrix_feeder.output.ready.eq(pooler.input.ready),
        ]

        # valid inputs
        for i, matrix_output in enumerate(matrix_feeder.output.data_ports()):
            comb += pooler.input[i].eq(matrix_output)
        # zero inputs
        for i in range(n_inputs, tree_n_inputs):
            comb += pooler.input[i].eq(0)

        # pooler --> output
        comb += [
            self.output.valid.eq(pooler.valid),
            self.output.last.eq(pooler.last),
            self.output.data.eq(pooler.data),
            pooler.ready.eq(self.output.ready),
        ]

        return m

