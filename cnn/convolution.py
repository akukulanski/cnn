from nmigen import *
from cnn.interfaces import AxiStreamMatrix, AxiStream
from cnn.matrix_feeder import MatrixFeeder
from cnn.farm import Farm

class Convolution(Elaboratable):
    
    def __init__(self, input_w, image_w, N, n_cores):
        self.image_w = image_w
        self.n_cores = n_cores
        self.matrix_feeder = MatrixFeeder(input_w=input_w,
                                          row_length=image_w,
                                          N=N,
                                          invert=False)
        self.farm = Farm(input_w=input_w,
                         shape=(N, N),
                         n_cores=n_cores)
        self.coeff = AxiStreamMatrix(width=input_w, shape=(N, N), direction='sink', name='coeff')
        self.input = AxiStream(width=input_w, direction='sink', name='input')
        self.output = AxiStream(width=self.output_w, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.coeff[f] for f in self.coeff.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    @property
    def input_w(self):
        return self.input.width

    @property
    def output_w(self):
        return self.farm.output.width

    @property
    def shape(self):
        return self.coeff.shape

    @property
    def N(self):
        return self.coeff.shape[0]
    

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        m.submodules.matrix_feeder = matrix_feeder = self.matrix_feeder
        m.submodules.farm = farm = self.farm

        # input --> matrix feeder
        comb += [matrix_feeder.input.valid.eq(self.input.valid),
                 matrix_feeder.input.last.eq(self.input.last),
                 matrix_feeder.input.data.eq(self.input.data),
                 self.input.ready.eq(matrix_feeder.input.ready),
                ]

        # matrix feeder --> farm
        comb += [farm.input_a.valid.eq(matrix_feeder.output.valid),
                 farm.input_a.last.eq(matrix_feeder.output.last),
                 farm.input_a.connect_data_ports(matrix_feeder.output),
                 matrix_feeder.output.ready.eq(farm.input_a.ready)
                ]
        
        # coeffs --> farm
        comb += [farm.input_b.valid.eq(self.coeff.valid),
                 farm.input_b.last.eq(self.coeff.last),
                 farm.input_b.connect_data_ports(self.coeff),
                 self.coeff.ready.eq(farm.input_b.ready),
                ]

        # farm --> output
        comb += [self.output.valid.eq(farm.output.valid),
                 self.output.last.eq(farm.output.last),
                 self.output.data.eq(farm.output.data),
                 farm.output.ready.eq(self.output.ready),
                ]

        return m

