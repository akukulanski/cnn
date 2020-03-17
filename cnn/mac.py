from nmigen import *

class MAC(Elaboratable):
    def __init__(self, input_w, output_w):
        self.input_w = input_w
        self.output_w = output_w
        self.input_a = Signal(self.input_w)
        self.input_b = Signal(self.input_w)
        self.clken = Signal()
        self.clr = Signal()
        self.output = Signal(self.output_w)
        self.valid_o = Signal()

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb
        
        clken_reg = Signal()
        input_a_reg = Signal(signed(self.input_w))
        input_b_reg = Signal(signed(self.input_w))
        mult = Signal(signed(int(2 * self.input_w + 1)))
        accumulator = Signal(signed(self.output_w))
        valid_o = Signal()


        comb += [mult.eq(input_a_reg * input_b_reg),
                 self.output.eq(accumulator),
                 self.valid_o.eq(valid_o),
                ]
        
        with m.If(self.clr):
            sync += [input_a_reg.eq(0),
                     input_b_reg.eq(0),
                     clken_reg.eq(0),
                     accumulator.eq(0),
                     valid_o.eq(0),
                    ]
        with m.Elif(self.clken):
            sync += [input_a_reg.eq(self.input_a),
                     input_b_reg.eq(self.input_b),
                     clken_reg.eq(self.clken),
                     accumulator.eq(accumulator + mult),
                     valid_o.eq(clken_reg),
                    ]

        return m
