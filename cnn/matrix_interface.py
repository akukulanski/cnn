from nmigen import *
import cnn.matrix as mat
from cnn.interfaces import MatrixStream


class MatrixInterfaceBypass(Elaboratable):
    
    def __init__(self, width, shape):
        self.width = width
        self.shape = shape
        self.input = MatrixStream(width=width, shape=shape, direction='sink', name='input')
        self.output = MatrixStream(width=width, shape=shape, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        dummy = Signal() # just to force the existence of a clock domain
        sync += dummy.eq(~dummy)

        comb += [self.output.valid.eq(self.input.valid),
                 self.output.last.eq(self.input.last),
                 self.input.ready.eq(self.output.ready),
                ]

        comb += self.output.connect_data_ports(self.input)

        #######################################################################
        #
        # > Alternative methods to connect dataports
        #
        # * Iterating through data_ports
        #
        # for data_i, data_o in zip(self.input.data_ports, self.output.data_ports):
        #     comb += data_o.eq(data_i)
        #
        #######################################################################

        return m