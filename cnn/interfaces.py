from nmigen import *
from nmigen.hdl.rec import Direction
import cnn.matrix as mat

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



class GenericStream(Dataport):

    def get_layout(self, direction):
        layout = Dataport.get_layout(self, direction)
        if direction == 'sink':
            layout += [('valid', 1, Direction.FANIN),
                       ('last', 1, Direction.FANIN),
                       ('ready', 1, Direction.FANOUT),]
        elif direction == 'source':
            layout += [('valid', 1, Direction.FANOUT),
                       ('last', 1, Direction.FANOUT),
                       ('ready', 1, Direction.FANIN)]
        else:
            raise ValueError(f'direction should be sink or source.')
        return layout

    def accepted(self):
        return (self.valid == 1) & (self.ready == 1)

    def is_last(self):
        return (self.accepted() == 1) & (self.last == 1)


class DataStream(GenericStream):
    def __init__(self, width, *args, **kargs):
        self.DATA_FIELDS = [('data', width)]
        GenericStream.__init__(self, *args, **kargs)


class MatrixStream(GenericStream):

    def __init__(self, width, shape, *args, **kwargs):
        self.shape = shape
        self.width = width
        self.DATA_FIELDS = []
        for idx in mat.matrix_indexes(shape):
            text_string = self.get_signal_name(idx)
            self.DATA_FIELDS.append((text_string, width))
        GenericStream.__init__(self, *args, **kwargs)

    def get_signal_name(self, indexes):
        return 'data_' + '_'.join([str(i) for i in indexes])

    @property
    def dimensions(self):
        return mat.get_dimensions(self.shape)

    @property
    def n_elements(self):
        return mat.get_n_elements(self.shape)

    @property
    def data_ports(self):
        for idx in mat.matrix_indexes(self.shape):
            yield getattr(self, self.get_signal_name(idx))

    def connect_data_ports(self, other):
        assert isinstance(other, MatrixStream)
        return [data_o.eq(data_i) for data_o, data_i in zip(self.data_ports, other.data_ports)]

    def connect_to_const(self, const=0):
        return [data_o.eq(const) for data_o in self.data_ports]

    @property
    def matrix(self):
        interface = self
        class MatrixPort():
            def __getitem__(self_mp, tup):
                if not hasattr(tup, '__iter__'):
                    tup = (tup,)
                assert len(tup) == len(interface.shape), f'{len(tup)} == {len(interface.shape)}'
                return getattr(interface, interface.get_signal_name(tup))
        return MatrixPort()

    @property
    def flatten_matrix(self):
        return [self.matrix[idx] for idx in mat.matrix_indexes(self.shape)]

        