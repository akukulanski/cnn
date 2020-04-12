import cocotb
from cocotb.drivers import BusDriver
from cocotb.triggers import RisingEdge
import random
from cnn.matrix import matrix_indexes, create_empty_matrix, get_matrix_element, set_matrix_element
from cores_nmigen.test.interfaces import AxiStreamDriver

class AxiStreamMatrixDriver(AxiStreamDriver):

    _signals =['TVALID', 'TREADY', 'TLAST']

    def __init__(self, entity, name, clock, shape):
        self.shape = shape
        for idx in matrix_indexes(self.shape):
            self._signals.append(self.get_element_name(idx))
        BusDriver.__init__(self, entity, name, clock)
        self.clk = clock
        self.buffer = []

    def get_element_name(self, indexes):
        return 'TDATA_' + '_'.join([str(i) for i in indexes])

    def get_element(self, indexes):
        return getattr(self.bus, self.get_element_name(indexes))
    
    def write(self, data):
        for idx in matrix_indexes(self.shape):
            self.get_element(idx) <= get_matrix_element(data, idx)

    def read(self):
        matrix = create_empty_matrix(self.shape)
        for idx in matrix_indexes(self.shape):
            set_matrix_element(matrix, idx, self.get_element(idx).value.integer)
        return matrix

    def init_sink(self):
        self.bus.TVALID <= 0
        self.bus.TLAST <= 0
        for idx in matrix_indexes(self.shape):
            self.get_element(idx) <= 0

    def init_source(self):
        self.bus.TREADY <= 0


