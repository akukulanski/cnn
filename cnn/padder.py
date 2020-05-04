from nmigen import *
from cnn.interfaces import DataStream
from cnn.utils.operations import _incr

_col_idx = 0
_row_idx = 1

class Padder(Elaboratable):
    """ 
    data_w          pixel width
    input_shape     input image shape (height, width)
    output_shape    output image shape (height, width)
    fill_value      padding fill value (default 0)
    """

    def __init__(self, data_w, input_shape, output_shape, fill_value=0):
        assert input_shape[0] <= output_shape[0], (
            f'input height > output height ({input_shape[0]} <= {output_shape[0]})')
        assert input_shape[1] <= output_shape[1], (
            f'input width > output width ({input_shape[1]} <= {output_shape[1]})')
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.fill_value = fill_value
        self.input = DataStream(width=data_w, direction='sink', name='input')
        self.output = DataStream(width=data_w, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        row_counter = Signal(range(self.output_shape[_row_idx]))
        col_counter = Signal(range(self.output_shape[_col_idx]))

        # Counters logic
        with m.If(self.output.accepted()):
            sync += row_counter.eq(_incr(row_counter, self.output_shape[_row_idx]))
            with m.If(row_counter == self.output_shape[_row_idx] - 1):
                sync += col_counter.eq(_incr(col_counter, self.output_shape[_col_idx]))
            with m.If(self.output.last):
                sync += [row_counter.eq(0),
                         col_counter.eq(0),
                        ]

        # Last generation logic
        with m.If((row_counter == self.output_shape[_row_idx] - 1) &
                  (col_counter == self.output_shape[_col_idx] - 1)):
            comb += self.output.last.eq(1)
        with m.Else():
            comb += self.output.last.eq(0)

        # Output data logic
        with m.If((row_counter < self.input_shape[_row_idx]) & (col_counter < self.input_shape[_col_idx])):
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


