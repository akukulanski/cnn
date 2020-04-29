import cocotb
from cocotb.drivers import BusDriver
from cocotb.triggers import RisingEdge
import random
import cnn.matrix as mat


class AxiStreamDriver(BusDriver):
    
    _signals =['TVALID', 'TREADY', 'TLAST', 'TDATA']

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        self.clk = clock
        self.buffer = []

    def accepted(self):
        return self.bus.TVALID.value.integer == 1 and self.bus.TREADY.value.integer == 1

    def write(self, data):
        self.bus.TDATA <= data

    def read(self):
        return self.bus.TDATA.value.integer

    def read_last(self):
        try:
            return self.bus.TLAST.value.integer
        except:
            return 0

    def _get_random_data(self):
        return random.randint(0, 2**len(self.bus.TDATA)-1)

    @cocotb.coroutine
    def monitor(self):
        while True:
            if self.accepted():
                self.buffer.append(self.read())
            yield RisingEdge(self.clk)

    @cocotb.coroutine
    def send(self, data, burps=False):
        data = list(data)
        while len(data):
            if burps:
                valid = random.randint(0, 1)
            else:
                valid = 1
            self.bus.TVALID <= valid
            if valid:
                self.write(data[0])
                self.bus.TLAST <= 1 if (len(data) == 1) else 0
            else:
                self.write(self._get_random_data())
                self.bus.TLAST <= 0
                # self.bus.TLAST <= random.randint(0, 1)
            yield RisingEdge(self.clk)
            if self.accepted():
                data.pop(0)
        self.bus.TVALID <= 0
        self.bus.TLAST <= 0

    @cocotb.coroutine
    def recv(self, n=-1, burps=False):
        rd = []
        while n:
            if burps:
                ready = random.randint(0, 1)
            else:
                ready = 1
            self.bus.TREADY <= ready
            yield RisingEdge(self.clk)
            if self.accepted():
                rd.append(self.read())
                n = n - 1
                if self.read_last():
                    break
        self.bus.TREADY <= 0
        return rd


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