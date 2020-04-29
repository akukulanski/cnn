from nmigen import *
from nmigen.hdl.rec import Direction
import cnn.matrix as mat

class GenericStream(Record):
    DATA_FIELDS = None
    def __init__(self, direction=None, name=None, fields=None, last=True):
        layout = self.get_layout(direction, last)
        Record.__init__(self, layout, name=name, fields=fields)
        self._total_width = sum([d[1] for d in self.DATA_FIELDS])
        self._flat_data = Cat(*[getattr(self, d[0]) for d in self.DATA_FIELDS])

    def get_layout(self, direction, last):
        if last:
            self.DATA_FIELDS += [('last', 1)]

        if direction == 'sink':
            layout = [('valid', 1, Direction.FANIN),
                      ('ready', 1, Direction.FANOUT)]
            layout += [(d[0], d[1], Direction.FANIN) for d in self.DATA_FIELDS]
        elif direction == 'source':
            layout = [('valid', 1, Direction.FANOUT),
                      ('ready', 1, Direction.FANIN)]
            layout += [(d[0], d[1], Direction.FANOUT) for d in self.DATA_FIELDS]
        else:
            raise ValueError(f'direction should be sink or source.')
        return layout

    def eq_from_flat(self, flat_data):
        ops = []
        start_bit = 0
        assert len(flat_data) == self._total_width
        for df in self.DATA_FIELDS:
            data, width = df[0], df[1]
            ops += [getattr(self, data).eq(flat_data[start_bit:start_bit+width])]
            start_bit += width
        return ops

    def accepted(self):
        return (self.valid == 1) & (self.ready == 1)


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

        