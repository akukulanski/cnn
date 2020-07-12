from nmigen import *
from cnn.utils.operations import _incr
from cnn.row_fifos import RowFifos
from cnn.interfaces import DataStream, MatrixStream
from cnn.resize import img_position_counter, is_last

class MatrixFeeder(Elaboratable):
    """ N fifos that work synchronized to provide NxN matrixes
    of data.
    This core has the intelligence to assert the valid output
    signal only when the current NxN matrix corresponds to
    a valid NxN submatrix of the image.
    """
    def __init__(self, data_w, input_shape, N, invert=False):
        self.input_shape = input_shape
        self.output_shape = (input_shape[0] + 1 - N, input_shape[1] + 1 - N)
        self.invert = invert
        self.input = DataStream(width=data_w, direction='sink', name='input')
        self.output = MatrixStream(width=data_w, shape=(N,N), direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    @property
    def data_w(self):
        return len(self.input.data)

    @property
    def shape(self):
        return self.output.dataport.shape

    @property
    def N(self):
        return self.output.dataport.shape[0]
    

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        image_w = self.input_shape[1]

        m.submodules.row_fifos = row_fifos = RowFifos(self.data_w, image_w, self.N, self.invert)
        m.submodules.submatrix_regs = submatrix = SubmatrixRegisters(self.data_w, self.N, self.invert)
        
        row, col = img_position_counter(m, sync, self.output, self.output_shape)
        comb += self.output.last.eq(is_last(row, col, self.output_shape))

        current_column = Signal(range(image_w))

        comb += [row_fifos.input.valid.eq(self.input.valid),
                 row_fifos.input.data.eq(self.input.data),
                 self.input.ready.eq(row_fifos.input.ready),
                ]

        comb += [submatrix.input.valid.eq(row_fifos.output.valid),
                 submatrix.input.dataport.eq(row_fifos.output.dataport),
                 row_fifos.output.ready.eq(submatrix.input.ready),
                ]

        comb += [self.output.dataport.eq(submatrix.output.dataport),
                ]

        with m.If(submatrix.output.accepted()):
            sync += current_column.eq(_incr(current_column, image_w))

        # logic to dismiss data when the output matrix is not
        # a valid submatrix of the input.
        with m.If(current_column < self.N - 1):
            comb += [self.output.valid.eq(0),
                     submatrix.output.ready.eq(1),
                    ]
        with m.Else():
            comb += [self.output.valid.eq(submatrix.output.valid),
                     submatrix.output.ready.eq(self.output.ready),
                    ]

        return m


class SubmatrixRegisters(Elaboratable):

    def __init__(self, data_w, N, invert=False):
        self.invert = invert
        self.input = MatrixStream(width=data_w, shape=(N,), direction='sink', name='input')
        self.output = MatrixStream(width=data_w, shape=(N,N), direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    @property
    def data_w(self):
        return self.input.dataport.width

    @property
    def shape_i(self):
        return self.input.dataport.shape

    @property
    def shape_o(self):
        return self.output.dataport.shape

    @property
    def N(self):
        return self.output.dataport.shape[0]

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        if self.invert:
            _col = lambda col: col
        else:
            _col = lambda col: self.N - 1 - col

        with m.If(self.input.accepted()):
            for row in range(self.N): # row iteration
                sync += self.output.dataport.matrix[row, _col(0)].eq(self.input.dataport.matrix[row]) # append column from input
                for col in range(1, self.N): # shift to the right the other columns
                    sync += self.output.dataport.matrix[row, _col(col)].eq(self.output.dataport.matrix[row, _col(col-1)])

        with m.If(self.input.accepted()):
            sync += self.output.valid.eq(1)
        with m.Elif(self.output.accepted()):
            sync += self.output.valid.eq(0)

        comb += self.input.ready.eq(self.output.accepted() | ~self.output.valid)

        return m