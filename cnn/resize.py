from nmigen import *
from cnn.interfaces import DataStream
from cnn.utils.operations import _incr

_col_idx = 0
_row_idx = 1


def img_position_counter(m, domain, interface, shape):
    row_counter = Signal(range(shape[_row_idx]))
    col_counter = Signal(range(shape[_col_idx]))
    with m.If(interface.accepted()):
        domain += row_counter.eq(_incr(row_counter, shape[_row_idx]))
        with m.If(row_counter == shape[_row_idx] - 1):
            domain += col_counter.eq(_incr(col_counter, shape[_col_idx]))
        with m.If(interface.last):
            domain += [row_counter.eq(0),
                       col_counter.eq(0),
                      ]
    return row_counter, col_counter

def is_last(row, col, shape):
    return Mux((row == shape[_row_idx] - 1) & (col == shape[_col_idx] - 1),
               1, 0)

def position_belongs_to_img(row, col, shape):
    return Mux((row < shape[_row_idx]) & (col < shape[_col_idx]),
               1, 0)


class Resizer(Elaboratable):
    """ 
    data_w          pixel width
    input_shape     input image shape (height, width)
    output_shape    output image shape (height, width)
    fill_value      padding fill value (default 0)
    """

    def __init__(self, data_w, input_shape, output_shape, fill_value=0):
        if input_shape[0] == output_shape[0] and input_shape[1] == output_shape[1]:
            # no operation, just last generation
            setattr(self, 'elaborate', self.elaborate_nop)
        elif input_shape[0] <= output_shape[0] and input_shape[1] <= output_shape[1]:
            setattr(self, 'elaborate', self.elaborate_padder)
        elif input_shape[0] >= output_shape[0] and input_shape[1] >= output_shape[1]:
            setattr(self, 'elaborate', self.elaborate_cropper)
        else:
            raise RuntimeError('Output image must be cant be bigger in one dimension and smaller in the other one')
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.fill_value = fill_value
        self.input = DataStream(width=data_w, direction='sink', name='input')
        self.output = DataStream(width=data_w, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate_padder(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        row, col = img_position_counter(m, sync, self.output, self.output_shape)

        comb += self.output.last.eq(is_last(row, col, self.output_shape))

        with m.If(position_belongs_to_img(row, col, self.input_shape)):
            comb += [self.output.valid.eq(self.input.valid),
                     self.output.data.eq(self.input.data),
                     self.input.ready.eq(self.output.ready),
                    ]
        with m.Else():
            comb += [self.output.valid.eq(1),
                     self.output.data.eq(self.fill_value),
                     self.input.ready.eq(0),
                    ]        

        return m

    def elaborate_cropper(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        row, col = img_position_counter(m, sync, self.input, self.input_shape)

        comb += self.output.last.eq(is_last(row, col, self.output_shape))

        with m.If(position_belongs_to_img(row, col, self.output_shape)):
            comb += [self.output.valid.eq(self.input.valid),
                     self.output.data.eq(self.input.data),
                     self.input.ready.eq(self.output.ready),
                    ]
        with m.Else():
            comb += [self.output.valid.eq(0),
                     self.output.data.eq(0),
                     self.input.ready.eq(1),
                    ]        

        return m

    def elaborate_nop(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        row, col = img_position_counter(m, sync, self.output, self.output_shape)

        comb += self.output.last.eq(is_last(row, col, self.output_shape))

        comb += [self.output.valid.eq(self.input.valid),
                 self.output.data.eq(self.input.data),
                 self.input.ready.eq(self.output.ready),
                ]

        return m
