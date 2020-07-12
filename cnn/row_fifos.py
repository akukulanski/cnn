from nmigen import *
from nmigen.lib.fifo import SyncFIFOBuffered
from cnn.interfaces import MatrixStream, DataStream
from cnn.utils.operations import _and


class RowFifos(Elaboratable):
    """ N fifos that work synchronized to provide Nx1 (N=row)
    vector of data.
    """

    def __init__(self, input_w, row_length, N, invert=False):
        self.row_length = row_length
        self.invert = invert
        self.input = DataStream(width=input_w, direction='sink', name='input')
        self.output = MatrixStream(width=input_w, shape=(N,), direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    @property
    def input_w(self):
        return len(self.input.data)

    @property
    def output_w(self):
        return self.output.dataport.width

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
                ]

        for n in range(self.N):
            if self.invert:
                comb += self.output.dataport.matrix[n].eq(fifo[n].r_data)
            else:
                comb += self.output.dataport.matrix[n].eq(fifo[self.N-1-n].r_data)

        return m


