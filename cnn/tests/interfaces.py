import cocotb
from cocotb.drivers import BusDriver
from cocotb.triggers import RisingEdge
import random
import cnn.matrix as mat
from cores_nmigen.test.interfaces import AxiStreamDriver

class AxiStreamMatrixDriver(AxiStreamDriver):

    _signals =['TVALID', 'TREADY', 'TLAST']

    def __init__(self, entity, name, clock, shape):
        self.shape = shape
        for idx in mat.matrix_indexes(self.shape):
            self._signals.append(self.get_element_name(idx))
        BusDriver.__init__(self, entity, name, clock)
        self.clk = clock
        self.buffer = []

    def get_element_name(self, indexes):
        return 'TDATA_' + '_'.join([str(i) for i in indexes])

    def get_element(self, indexes):
        return getattr(self.bus, self.get_element_name(indexes))
    
    def write(self, data):
        for idx in mat.matrix_indexes(self.shape):
            self.get_element(idx) <= mat.get_matrix_element(data, idx)

    def read(self):
        matrix = mat.create_empty_matrix(self.shape)
        for idx in mat.matrix_indexes(self.shape):
            mat.set_matrix_element(matrix, idx, self.get_element(idx).value.integer)
        return matrix

    def _get_random_data(self):
        matrix = mat.create_empty_matrix(self.shape)
        for idx in mat.matrix_indexes(self.shape):
            mat.set_matrix_element(matrix, idx, random.randint(0, self._max_value))
        return matrix

    @property
    def _max_value(self):
        width = len(self.get_element(self.first_idx))
        return 2**width - 1

    def init_sink(self):
        self.bus.TVALID <= 0
        self.bus.TLAST <= 0
        for idx in mat.matrix_indexes(self.shape):
            self.get_element(idx) <= 0

    def init_source(self):
        self.bus.TREADY <= 0

    @property
    def first_idx(self):
        return tuple([0] * len(self.shape))