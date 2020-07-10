from nmigen import *
from cnn.interfaces import DataStream, MatrixStream
from cnn.matrix_feeder import MatrixFeeder
from cnn.tree_operations_wrapped import TreeHighestUnsignedWrapped
from cnn.utils.operations import _incr
from cnn.resize import img_position_counter, is_last
from math import ceil, log2


class MatrixFeederSkip(MatrixFeeder):
    
    def __init__(self, data_w, input_shape, N, invert=False):
        assert input_shape[0] % N == 0, (
            f'image height must be a multiple of N. Psss, you can use Padder() to append zeros!')
        assert input_shape[1] % N == 0, (
            f'image width must be a multiple of N. Psss, you can use Padder() to append zeros!')
        self.input = DataStream(width=data_w, direction='sink', name='input')
        self.output = MatrixStream(width=data_w, shape=(N,N), direction='source', name='output')
        self.matrix_feeder = MatrixFeeder(data_w, input_shape, N, invert=invert)
        self.output_shape = (int(input_shape[0] / N), int(input_shape[1] / N))

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        pooling_counter_row = Signal(range(self.N))
        pooling_counter_col = Signal(range(self.N))


        m.submodules.matrix_feeder = matrix_feeder = self.matrix_feeder

        row, col = img_position_counter(m, sync, self.output, self.output_shape)
        feeder_row, feeder_col = img_position_counter(m, sync, matrix_feeder.output, matrix_feeder.output_shape)

        # input --> matrix_feeder
        comb += [
            matrix_feeder.input.valid.eq(self.input.valid),
            matrix_feeder.input.last.eq(self.input.last),
            matrix_feeder.input.data.eq(self.input.data),
            self.input.ready.eq(matrix_feeder.input.ready),
        ]

        comb += self.output.connect_data_ports(matrix_feeder.output)
        comb += self.output.last.eq(is_last(row, col, self.output_shape))

        with m.If(matrix_feeder.output.accepted()):
            sync += pooling_counter_row.eq(_incr(pooling_counter_row, self.N))
            with m.If(feeder_row == matrix_feeder.output_shape[1] - 1):
                sync += pooling_counter_row.eq(0)
                sync += pooling_counter_col.eq(_incr(pooling_counter_col, self.N))
            with m.If(matrix_feeder.output.last):
                sync += [
                    pooling_counter_row.eq(0),
                    pooling_counter_col.eq(0),
                ]

        with m.FSM() as fsm:
            with m.State("normal"):
                with m.If((pooling_counter_row == 0) & (pooling_counter_col == 0)):
                    comb += [
                        self.output.valid.eq(matrix_feeder.output.valid),
                        matrix_feeder.output.ready.eq(self.output.ready),
                    ]
                with m.Else():
                    comb += [
                        self.output.valid.eq(0),
                        matrix_feeder.output.ready.eq(1),
                    ]
                with m.If(self.output.accepted() & self.output.last):
                    m.next = "last"

            with m.State("last"):
                comb += [
                    self.output.valid.eq(0),
                    matrix_feeder.output.ready.eq(1),
                ]
                with m.If(self.input.accepted() & self.input.last):
                    m.next = "normal"

        

        return m


class Pooling(Elaboratable):

    _modes = {
        'highest': TreeHighestUnsignedWrapped
    }
    
    def __init__(self, data_w, input_shape, N, mode):
        assert input_shape[0] % N == 0, (
            f'image height must be a multiple of N. Psss, you can use Padder() to append zeros!')
        assert input_shape[1] % N == 0, (
            f'image width must be a multiple of N. Psss, you can use Padder() to append zeros!')
        assert mode in self._modes, 'Unsupported mode'
        self.mode = mode
        self.matrix_feeder = MatrixFeederSkip(data_w=data_w,
                                              input_shape=input_shape,
                                              N=N,
                                              invert=False)
        self.input = DataStream(width=data_w, direction='sink', name='input')
        self.output = DataStream(width=data_w, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    @property
    def N(self):
        return self.matrix_feeder.shape[0]

    @property
    def output_shape(self):
        return [int(x/self.N) for x in self.input_shape]

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        pooling_core = self._modes[self.mode]

        n_inputs = self.matrix_feeder.N ** 2
        tree_n_stages = int(ceil(log2(n_inputs)))

        m.submodules.matrix_feeder = matrix_feeder = self.matrix_feeder
        m.submodules.pooler = pooler = pooling_core(width_i=self.input.width,
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
            comb += pooler.input.matrix[i].eq(matrix_output)
        # zero inputs
        for i in range(n_inputs, tree_n_inputs):
            comb += pooler.input.matrix[i].eq(0)

        # pooler --> output
        comb += [
            self.output.valid.eq(pooler.output.valid),
            self.output.last.eq(pooler.output.last),
            self.output.data.eq(pooler.output.data),
            pooler.output.ready.eq(self.output.ready),
        ]

        return m

