from nmigen import *
from nmigen.hdl.rec import Direction
import cnn.matrix as mat

class MetaStream(Record):
    DATA_FIELDS = []
    def __init__(self, width, direction=None, name=None, fields=None):
        self.width = width
        if direction == 'sink':
            layout = [('TVALID', 1, Direction.FANIN),
                      ('TREADY', 1, Direction.FANOUT),
                      ('TLAST', 1, Direction.FANIN)]
            for d in self.DATA_FIELDS:
                layout.append((d[0], d[1], Direction.FANIN))
        elif direction == 'source':
            layout = [('TVALID', 1, Direction.FANOUT),
                      ('TREADY', 1, Direction.FANIN),
                      ('TLAST', 1, Direction.FANOUT)]
            for d in self.DATA_FIELDS:
                layout.append((d[0], d[1], Direction.FANOUT))
        else:
            layout = [('TVALID', 1),
                      ('TREADY', 1),
                      ('TLAST', 1)]
            for d in self.DATA_FIELDS:
                layout.append((d[0], d[1]))
        Record.__init__(self, layout, name=name, fields=fields)
        self.valid = self.TVALID
        self.ready = self.TREADY
        self.last = self.TLAST
        
    def accepted(self):
        return (self.valid == 1) & (self.ready == 1)


class AxiStream(MetaStream):
    def __init__(self, width, direction=None, name=None, fields=None):
        self.DATA_FIELDS = [('TDATA', width)]
        MetaStream.__init__(self, width, direction, name=name, fields=fields)
        self.data = self.TDATA


class AxiStreamMatrix(MetaStream):

    def __init__(self, width, shape, direction=None, name=None, fields=None):
        self.shape = shape
        self.width = width
        self.DATA_FIELDS = []
        for idx in mat.matrix_indexes(shape):
            text_string = self.get_signal_name(idx)
            self.DATA_FIELDS.append((text_string, width))
        MetaStream.__init__(self, width, direction=direction, name=name, fields=fields)

    def get_signal_name(self, indexes):
        return 'TDATA_' + '_'.join([str(i) for i in indexes])

    @property
    def dimensions(self):
        return mat.get_dimensions(self.shape)

    @property
    def n_elements(self):
        return mat.get_n_elements(self.shape)

    def accepted(self):
        return (self.TVALID == 1) & (self.TREADY == 1)

    @property
    def data_ports(self):
        for idx in mat.matrix_indexes(self.shape):
            yield getattr(self, self.get_signal_name(idx))

    def connect_data_ports(self, other):
        assert isinstance(other, AxiStreamMatrix)
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