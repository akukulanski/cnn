import cocotb
from cocotb.drivers import BusDriver
from cocotb.triggers import RisingEdge
from cnn.interfaces import name_from_index, shaped_idx
import random
import numpy as np

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
            valid = random.randint(0, 1) if burps else 1
            self.bus.valid <= valid
            if valid:
                self.write(data[0])
                self.bus.last <= 1 if (len(data) == 1) else 0
            else:
                self.write(self._get_random_data())
                self.bus.last <= 0
            yield RisingEdge(self.clk)
            if self.accepted():
                data.pop(0)
        self.bus.valid <= 0
        self.bus.last <= 0

    @cocotb.coroutine
    def recv(self, n=-1, burps=False):
        rd = []
        while n:
            ready = random.randint(0, 1) if burps else 1
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
        return random.randint(*_signed_limits(width))


class MatrixStreamDriver(MetaStreamDriver):

    def __init__(self, entity, name, clock, shape):
        self.shape = shape
        self.dimensions = len(shape)
        self.n_elements = int(np.prod(shape))
        self._signals = []
        for idx in range(self.n_elements):
            self._signals.append(name_from_index(shaped_idx(idx, shape)))
        MetaStreamDriver.__init__(self, entity, name, clock)
        self.width = len(self.matrix[shaped_idx(0, self.shape)])

    def write(self, data):
        assert len(data) == self.n_elements
        for i, d in enumerate(data):
            self.matrix[shaped_idx(i, self.shape)] <= d

    def read(self):
        r = []
        for i in range(self.n_elements):
            r.append(self.matrix[shaped_idx(i, self.shape)].value.integer)
        return r

    def _get_random_data(self):
        return [random.getrandbits(self.width) for _ in range(self.n_elements)]

    def init_master(self):
        MetaStreamDriver.init_master(self)
        for i in range(self.n_elements):
            self.matrix[shaped_idx(i, self.shape)] <= 0

    @property
    def matrix(self):
        interface = self
        class MatrixPort():
            def __getitem__(self, tup):
                if not hasattr(tup, '__iter__'):
                    tup = (tup,)
                assert len(tup) == len(interface.shape), f'{len(tup)} == {len(interface.shape)}'
                return getattr(interface.bus, name_from_index(tup))
        return MatrixPort()    

class SignedMatrixStreamDriver(MatrixStreamDriver):
    def read(self):
        r = []
        for i in range(self.n_elements):
            r.append(self.matrix[shaped_idx(i, self.shape)].value.signed_integer)
        return r

    def _get_random_data(self):
        return [random.randint(*_signed_limits(self.width)) for _ in range(self.n_elements)]
