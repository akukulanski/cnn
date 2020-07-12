from nmigen import *
from nmigen.hdl.rec import Direction
import numpy as np

class DataPort(Record):

    def __init__(self, width, direction, layout=None, name=None, fields=None):
        assert direction in ('sink', 'source')
        self.direction = direction
        d = Direction.FANIN if direction == 'sink' else Direction.FANOUT
        if layout is None:
            layout = []
        layout += [
            ('data', width, d),
        ]
        Record.__init__(self, layout, name=name, fields=fields)
        self.flat = Cat(*[sig for n, sig in self.fields.items()])
        self.width = len(self.data)


class ComplexPort(Record):

    def __init__(self, width, direction, layout=None, name=None, fields=None):
        assert direction in ('sink', 'source')
        self.direction = direction
        if not isinstance(width, Shape):
            width = signed(width)
        d = Direction.FANIN if direction == 'sink' else Direction.FANOUT
        if layout is None:
            layout = []
        layout += [
            ('real', width, d),
            ('imag', width, d),
        ]
        Record.__init__(self, layout, name=name, fields=fields)
        self.flat = Cat(*[self.real, self.imag])
        self.width = len(self.real)


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

class MatrixPort(Record):

    def __init__(self, width, shape, direction, layout=None, name=None, fields=None):
        assert direction in ('sink', 'source')
        self.shape = shape
        self.dimensions = len(shape)
        self.n_elements = int(np.prod(shape))
        self.direction = direction
        d = Direction.FANIN if direction == 'sink' else Direction.FANOUT
        if layout is None:
            layout = []
        for i in range(self.n_elements):
            sig_name = name_from_index(shaped_idx(i, shape))
            layout += [(sig_name, width, d)]
        Record.__init__(self, layout, name=name, fields=fields)
        self.flat = Cat(*[sig for n, sig in self.fields.items()])
        self.width = len(self[name_from_index(shaped_idx(0, shape))])

    def eq(self, other):
        assert isinstance(other, MatrixPort)
        return self.flat.eq(other.flat)

    def eq_const(self, const=0):
        return [sig.eq(const) for _, sig in self.fields.items()]

    @property
    def matrix(self):
        interface = self
        class MyMatrix():
            def __getitem__(self, tup):
                if not hasattr(tup, '__iter__'):
                    tup = (tup,)
                assert len(tup) == len(interface.shape), f'{len(tup)} == {len(interface.shape)}'
                return interface[name_from_index(tup)]
        return MyMatrix()


class StreamPort(Record):

    _source_driven_signals = [('valid', 1), ('last', 1)]
    _sink_driven_signals = [('ready', 1)]
    
    def __init__(self, direction, layout=None, name=None, fields=None):
        assert direction in ('sink', 'source')
        self.direction = direction

        if layout is None:
            layout = []

        _data_fields = fields
        
        stream_layout = []
        if self.direction == 'sink':
            stream_layout += [(n, w, Direction.FANIN) for n, w in self._source_driven_signals]
            stream_layout += [(n, w, Direction.FANOUT) for n, w in self._sink_driven_signals]
        elif self.direction == 'source':
            stream_layout += [(n, w, Direction.FANOUT) for n, w in self._source_driven_signals]
            stream_layout += [(n, w, Direction.FANIN) for n, w in self._sink_driven_signals]

        Record.__init__(self, layout + stream_layout, name=name, fields=fields)
        
        self.data_ports = [self[x] for x in _data_fields]
        self.stream_ports = [self[n] for n, _, __ in stream_layout]
        self.flat = Cat(*self.data_ports)

    def accepted(self):
        return (self.valid == 1) & (self.ready == 1)

    def is_last(self):
        return (self.accepted() == 1) & (self.last == 1)


class Stream(StreamPort):
    def __init__(self, dataport):
        self.dataport = dataport
        StreamPort.__init__(self,
                            direction=dataport.direction,
                            layout=list(dataport.layout),
                            name=dataport.name,
                            fields=dataport.fields)


def DataStream(*args, **kwargs):
    dataport = DataPort(*args, **kwargs)
    return Stream(dataport=dataport)


def MatrixStream(*args, **kwargs):
    dataport = MatrixPort(*args, **kwargs)
    return Stream(dataport=dataport)

