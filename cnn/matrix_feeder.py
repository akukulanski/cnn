from nmigen import *
from nmigen.lib.fifo import SyncFIFOBuffered
from cores_nmigen.interfaces import AxiStream

def _and(signals):
    return Mux(Cat(*signals) == 2**len(signals)-1, 1, 0)

def _or(signals):
    return Mux(Cat(*signals) != 0, 1, 0)

class MatrixFeeder(Elaboratable):
    """ N fifos that work synchronized to provide NxN matrixes
    of data.
    """
    def __init__(self, input_w, row_length, N):
        self.input_w = input_w
        self.row_length = row_length
        self.N = N
        self.output_w = input_w * N**2
        self.input = AxiStream(width=self.input_w, direction='sink', name='input')
        self.output = AxiStream(width=self.output_w, N=N, M=N, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        m.submodules.row_fifos = row_fifos = RowFifos(self.input_w, self.row_length, self.N)

        registers = [Signal(self.input_w * self.N) for _ in range(self.N)]
        current_column = Signal(range(self.row_length))

        comb += row_fifos.input.eq(self.input)

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
            comb += self.output.data[start_idx:stop_idx].eq(Cat(*[registers[n][reg_start_idx:reg_stop_idx] for n in range(self.N)]))

        return m


class RowFifos(Elaboratable):
    """ N fifos that work synchronized to provide Nx1 (N=row)
    vector of data.
    """

    def __init__(self, input_w, row_length, N, endianness=-1):
        assert endianness in (-1, 1)
        self.input_w = input_w
        self.row_length = row_length
        self.N = N
        self.endianness = endianness
        self.output_w = input_w * N
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

        fifo = [SyncFIFOBuffered(width=self.input_w, depth=self.row_length+4) for _ in range(self.N)]

        fifo_r_rdy = [Signal() for _ in range(self.N)]
        fifo_r_valid = [Signal() for _ in range(self.N)]

        w_en = [Signal() for _ in range(self.N - 1)]

        for n in range(self.N):
            m.submodules['fifo_' + str(n)] = fifo[n]
            comb += [fifo_r_rdy[n].eq((fifo[n].level < self.row_length) | self.output.accepted()),
                    ]

        # first fifo
        comb += [self.input.ready.eq(fifo[0].w_rdy),
                 fifo[0].w_en.eq(self.input.accepted()),
                 fifo[0].w_data.eq(self.input.data),
                ]

        for n in range(self.N - 1):
            comb += [fifo_r_valid[n].eq((fifo[n+1].level == self.row_length) & (fifo[n].r_rdy)),
                     fifo[n].r_en.eq((self.output.accepted() | ~fifo_r_valid[n])),
                     fifo[n+1].w_en.eq(fifo[n].r_rdy & fifo[n].r_en),
                     fifo[n+1].w_data.eq(fifo[n].r_data),
                    ]

        # last fifo
        n = self.N - 1
        comb += [fifo_r_valid[n].eq(fifo[n].r_rdy),
                 fifo[n].r_en.eq(self.output.accepted()),
                ]
        
        # output
        comb += [self.output.valid.eq(_and(fifo_r_valid)),
                 self.output.data.eq(Cat(*[fifo[n].r_data for n in range(self.N)[::self.endianness]])),
                ]

        return m


