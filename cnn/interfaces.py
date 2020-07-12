from nmigen import *
from nmigen.hdl.rec import Direction
import cnn.matrix as mat
import numpy as np

class Dataport(Record):

    DATA_FIELDS = None

    def __init__(self, direction=None, name=None, fields=None):
        layout = self.get_layout(direction)
        Record.__init__(self, layout, name=name, fields=fields)

    @property
    def total_width(self):
        return sum([width for name, width in self.DATA_FIELDS])

    def flatten(self):
        return Cat(*[getattr(self, data) for data, width in self.DATA_FIELDS])

    def get_layout(self, direction):
        if direction == 'sink':
            layout = [(name, width, Direction.FANIN) for name, width in self.DATA_FIELDS]
        elif direction == 'source':
            layout = [(name, width, Direction.FANOUT) for name, width in self.DATA_FIELDS]
        else:
            raise ValueError(f'direction should be sink or source.')
        return layout

    def eq_from_flat(self, flat_data):
        ops = []
        start_bit = 0
        assert len(flat_data) == self.total_width
        for name, width in self.DATA_FIELDS:
            ops += [getattr(self, name).eq(flat_data[start_bit:start_bit+width])]
            start_bit += width
        return ops

    def data_ports(self):
        return [getattr(self, name) for name, _ in self.DATA_FIELDS]

    def connect_source(self, other):
        ops = []
        for name, width in self.DATA_FIELDS:
            ops.append(getattr(self, name).eq(getattr(other, name)))
        return ops



class GenericStream(Dataport):

    _source_driven_signals = [('valid', 1), ('last', 1)]
    _sink_driven_signals = [('ready', 1)]

    def get_layout(self, direction):
        layout = Dataport.get_layout(self, direction)
        if direction == 'sink':
            layout += [(n, w, Direction.FANIN) for n, w in self._source_driven_signals]
            layout += [(n, w, Direction.FANOUT) for n, w in self._sink_driven_signals]
        elif direction == 'source':
            layout += [(n, w, Direction.FANOUT) for n, w in self._source_driven_signals]
            layout += [(n, w, Direction.FANIN) for n, w in self._sink_driven_signals]
        else:
            raise ValueError(f'direction should be sink or source.')
        return layout

    def accepted(self):
        return (self.valid == 1) & (self.ready == 1)

    def is_last(self):
        return (self.accepted() == 1) & (self.last == 1)

    def connect_source(self, other):
        ops = Dataport.connect_source(self, other)
        for n, w in self._source_driven_signals:
            ops.append(getattr(self, n).eq(getattr(other, n)))
        for n, w in self._sink_driven_signals:
            ops.append(getattr(other, n).eq(getattr(self, n)))



class DataStream(GenericStream):
    def __init__(self, width, *args, **kargs):
        self.DATA_FIELDS = [('data', width)]
        self.width = width
        GenericStream.__init__(self, *args, **kargs)


def flat_idx(idx, shape):
    assert len(idx) == len(shape), f'{len(idx)} != {len(shape)}'
    for i, s in zip(idx, shape):
        assert i < s, f'{i} >= {s}'
    t = 0
    for i, v in enumerate(idx):
        gran = np.prod(shape[i+1:])
        t += gran * v
    return t

def shaped_idx(idx, shape):
    t = []
    for i, s in enumerate(shape):
        gran = np.prod(shape[i+1:])
        t.append(int(idx / gran))
        idx = int(idx % gran)
    return t

def name_from_index(indexes):
    return 'data_' + '_'.join([str(i) for i in indexes])

class MatrixStream(GenericStream):

    def __init__(self, width, shape, *args, **kwargs):
        self.shape = shape
        self.width = width
        self.dimensions = len(shape)
        self.n_elements = int(np.prod(shape))
        self.DATA_FIELDS = []
        for i in range(self.n_elements):
            name = name_from_index(shaped_idx(i, shape))
            self.DATA_FIELDS.append((name, width))
        GenericStream.__init__(self, *args, **kwargs)
        self.flat = Cat(*self.data_ports())

    def data_ports(self):
        data_ports = []
        for i in range(self.n_elements):
            name = name_from_index(shaped_idx(i, self.shape))
            yield self[name]

    def connect_data_ports(self, other):
        assert isinstance(other, MatrixStream)
        return [data_o.eq(data_i) for data_o, data_i in zip(self.data_ports(), other.data_ports())]

    def connect_to_const(self, const=0):
        return [data_o.eq(const) for data_o in self.data_ports()]

    @property
    def matrix(self):
        interface = self
        class MatrixPort():
            def __getitem__(self, tup):
                if not hasattr(tup, '__iter__'):
                    tup = (tup,)
                assert len(tup) == len(interface.shape), f'{len(tup)} == {len(interface.shape)}'
                return interface[name_from_index(tup)]
        return MatrixPort()

