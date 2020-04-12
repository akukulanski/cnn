from cores_nmigen.interfaces import MetaStream
import cnn.matrix as mat


class MatrixPort():

    def __init__(self, interface):
        self.interface = interface

    def __getitem__(self, tup):
        if not hasattr(tup, '__iter__'):
            tup = (tup,)
        assert len(tup) == len(self.interface.shape), f'{len(tup)} == {len(self.interface.shape)}'
        return getattr(self.interface, self.interface.get_signal_name(tup))


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
    def matrix(self):
        return MatrixPort(self)
    

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

