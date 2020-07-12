from nmigen import *
from cnn.interfaces import MatrixStream, DataStream
from cnn.matrix_feeder import MatrixFeeder
from cnn.farm import Farm

class Convolution(Elaboratable):
    _doc_ = """
    Convolution of an input image with an NxN kernel.

    Interfaces
    ----------
    input : Stream, input
        Input image, where each data is an incomming pixel.

    coeff : Matrix Stream, input
        Kernel coefficients.
        TO DO: should not be a stream, but plain "matrix shaped" values.


    Parameters
    ----------
    width : int
        Bit width of both the image data and kernel coefficients.

    input_shape : tuple
        Image input shape (rows, columns).

    N : int
        Kernel size (NxN)

    n_cores : int
        Number of paralell computations of dot product.
    """
    
    def __init__(self, width, input_shape, N, n_cores):
        self.input_shape = input_shape
        self.n_cores = n_cores
        self.matrix_feeder = MatrixFeeder(data_w=width,
                                          input_shape=input_shape,
                                          N=N,
                                          invert=False)
        self.farm = Farm(width=width,
                         shape=(N, N),
                         n_cores=n_cores)
        self.coeff = MatrixStream(width=width, shape=(N, N), direction='sink', name='coeff')
        self.input = DataStream(width=width, direction='sink', name='input')
        self.output = DataStream(width=len(self.farm.output.data), direction='source', name='output')
        self.input_w = len(self.input.data)
        self.output_w = len(self.output.data)
        self.shape = self.coeff.dataport.shape
        self.N = self.coeff.dataport.shape[0]

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.coeff[f] for f in self.coeff.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports


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
                 farm.input_a.dataport.eq(matrix_feeder.output.dataport),
                 matrix_feeder.output.ready.eq(farm.input_a.ready)
                ]
        
        # coeffs --> farm
        comb += [farm.input_b.valid.eq(self.coeff.valid),
                 farm.input_b.last.eq(self.coeff.last),
                 farm.input_b.dataport.eq(self.coeff.dataport),
                 self.coeff.ready.eq(farm.input_b.ready),
                ]

        # farm --> output
        comb += [self.output.valid.eq(farm.output.valid),
                 self.output.last.eq(farm.output.last),
                 self.output.data.eq(farm.output.data),
                 farm.output.ready.eq(self.output.ready),
                ]

        return m

