import cocotb
from cocotb.drivers import BusDriver
from cocotb.triggers import RisingEdge
import random
import cnn.matrix as mat

_signed_limits = lambda width: (-2**(width-1), 2**(width-1)-1)

class MetaStreamDriver(BusDriver):

    def __init__(self, entity, name, clock):
        self._signals += ['valid', 'ready', 'last']
        BusDriver.__init__(self, entity, name, clock)
        self.clk = clock
        self.buffer = []

    def accepted(self):
        return self.bus.valid.value.integer == 1 and self.bus.ready.value.integer == 1

    def read_last(self):
        try:
            return self.bus.last.value.integer
        except:
            return 0

    def init_master(self):
        self.bus.valid <= 0
        self.bus.last <= 0

    def init_slave(self):
        self.bus.ready <= 0

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
            self.bus.valid <= valid
            if valid:
                self.write(data[0])
                self.bus.last <= 1 if (len(data) == 1) else 0
            else:
                self.write(self._get_random_data())
                self.bus.last <= 0
                # self.bus.last <= random.randint(0, 1)
            yield RisingEdge(self.clk)
            if self.accepted():
                data.pop(0)
        self.bus.valid <= 0
        self.bus.last <= 0

    @cocotb.coroutine
    def recv(self, n=-1, burps=False):
        rd = []
        while n:
            if burps:
                ready = random.randint(0, 1)
            else:
                ready = 1
            self.bus.ready <= ready
            yield RisingEdge(self.clk)
            if self.accepted():
                rd.append(self.read())
                n = n - 1
                if self.read_last():
                    break
        self.bus.ready <= 0
        return rd


class StreamDriver(MetaStreamDriver):

    def __init__(self, entity, name, clock):
        self._signals = ['data']
        MetaStreamDriver.__init__(self, entity, name, clock)

    def write(self, data):
        self.bus.data <= data

    def read(self):
        return self.bus.data.value.integer

    def init_master(self):
        MetaStreamDriver.init_master(self)
        self.write(0)

    def _get_random_data(self):
        return random.getrandbits(len(self.bus.data))


class SignedStreamDriver(StreamDriver):
    def read(self):
        return self.bus.data.value.signed_integer

    def _get_random_data(self):
        width = len(self.bus.data)
        # _min, _max = -2**(width-1), 2**(width-1)-1
        # return random.randint(_min, _max)
        return random.randint(*_signed_limits(width))


class MatrixStreamDriver(MetaStreamDriver):

    def __init__(self, entity, name, clock, shape):
        self.shape = shape
        self._signals = [self.get_element_name(idx) for idx in mat.matrix_indexes(self.shape)]
        MetaStreamDriver.__init__(self, entity, name, clock)

    def get_element_name(self, indexes):
        return 'data_' + '_'.join([str(i) for i in indexes])

    def get_element(self, indexes):
        return getattr(self.bus, self.get_element_name(indexes))
    
    def write(self, data):
        for idx in mat.matrix_indexes(self.shape):
            self.get_element(idx) <= mat.get_matrix_element(data, idx)

    def read(self):
        matrix = mat.create_empty_matrix(self.shape)
        for idx in mat.matrix_indexes(self.shape):
            val = self.get_element(idx).value.integer
            mat.set_matrix_element(matrix, idx, val)
        return matrix

    def _get_random_data(self):
        matrix = mat.create_empty_matrix(self.shape)
        for idx in mat.matrix_indexes(self.shape):
            mat.set_matrix_element(matrix, idx, random.getrandbits(self.width))
        return matrix

    @property
    def width(self):
        return len(self.get_element(self.first_idx))

    @property
    def first_idx(self):
        return tuple([0] * len(self.shape))

    def init_master(self):
        MetaStreamDriver.init_master(self)
        for idx in mat.matrix_indexes(self.shape):
            self.get_element(idx) <= 0

class SignedMatrixStreamDriver(MatrixStreamDriver):
    def read(self):
        matrix = mat.create_empty_matrix(self.shape)
        for idx in mat.matrix_indexes(self.shape):
            val = self.get_element(idx).value.signed_integer
            mat.set_matrix_element(matrix, idx, val)
        return matrix

    def _get_random_data(self):
        matrix = mat.create_empty_matrix(self.shape)
        for idx in mat.matrix_indexes(self.shape):
            mat.set_matrix_element(matrix, idx, random.randint(*_signed_limits(self.width)))
        return matrix