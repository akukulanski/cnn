from nmigen import *
from cores_nmigen.interfaces import AxiStream
from cores_nmigen.operations import _incr, _and, _or
from cnn.row_fifos import RowFifos

class MatrixFeeder(Elaboratable):
    """ N fifos that work synchronized to provide NxN matrixes
    of data.
    This core has the intelligence to assert the valid output
    signal only when the current NxN matrix corresponds to
    a valid NxN submatrix of the image.
    """
    def __init__(self, input_w, row_length, N, endianness=-1):
        self.input_w = input_w
        self.row_length = row_length
        self.N = N
        self.endianness = endianness
        self.output_w = input_w * N**2
        self.input = AxiStream(width=self.input_w, direction='sink', name='input')
        self.output = AxiStream(width=self.output_w, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        m.submodules.row_fifos = row_fifos = RowFifos(self.input_w, self.row_length, self.N, self.endianness)

        registers = Array([Signal(self.input_w * self.N) for _ in range(self.N)])
        current_column = Signal(range(self.row_length))

        comb += [row_fifos.input.valid.eq(self.input.valid),
                 row_fifos.input.data.eq(self.input.data),
                 self.input.ready.eq(row_fifos.input.ready),
                ]

        with m.If(row_fifos.output.accepted()):
            sync += current_column.eq(_incr(current_column, self.row_length))
            with m.If(current_column < self.N - 1):
                sync += self.output.valid.eq(0)
            with m.Else():
                sync += self.output.valid.eq(1)
            sync += registers[0].eq(row_fifos.output.data)
            for n in range(1, self.N):
                sync += registers[n].eq(registers[n-1])

        comb += row_fifos.output.ready.eq(self.output.accepted() | ~self.output.valid)

        for row in range(self.N):
            start_idx = self.input_w * self.N * row
            stop_idx = self.input_w * self.N * (row + 1)
            reg_start_idx = self.input_w * row
            reg_stop_idx = self.input_w * (row + 1)
            comb += self.output.data[start_idx:stop_idx].eq(Cat(*[registers[n][reg_start_idx:reg_stop_idx] for n in range(self.N)[::self.endianness]]))

        return m
