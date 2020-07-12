from nmigen import *
from cnn.mac import MAC
from cnn.utils.bits import required_bits
from cnn.interfaces import DataStream, MatrixStream

def calculate_output_width(width_i, n_inputs):
    worst_value = -2**(width_i - 1)
    worst_mult = worst_value ** 2
    worst_result = worst_mult * n_inputs
    return required_bits(worst_result)

class DotProduct(Elaboratable):
    #
    # WARNING:
    # The dataflow is controlled ONLY by the input_a AXIS interface.
    # The input_b AXIS interface is DUMMY, and should always have valid values in the input.
    # The ready of the input_b interface will be attached to input_a.accepted(), and a valid=1
    # will be assumed.
    #
    # Why?
    # I want to avoid a combinational path between the valid of input_b and the ready of input_a.
    #
    def __init__(self, width_i, shape):
        self.input_a = MatrixStream(width=width_i, shape=shape, direction='sink', name='input_a')
        self.input_b = MatrixStream(width=width_i, shape=shape, direction='sink', name='input_b')
        self.input_w = self.input_a.dataport.width
        self.n_inputs = self.input_a.dataport.n_elements
        self.output_w = calculate_output_width(self.input_w, self.n_inputs)
        self.output = DataStream(self.output_w, direction='source', name='output')
        self.shape = self.input_a.dataport.shape

    def get_ports(self):
        ports = []
        ports += [self.input_a[f] for f in self.input_a.fields]
        ports += [self.input_b[f] for f in self.input_b.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        tmp_input_a = Signal(self.input_w * self.n_inputs)
        tmp_input_b = Signal(self.input_w * self.n_inputs)
        counter = Signal(range(self.n_inputs))
        
        m.submodules['mac'] = mac = MAC(input_w=self.input_w, output_w=self.output_w)
        comb += [mac.input_a.eq(tmp_input_a[0:self.input_w]),
                 mac.input_b.eq(tmp_input_b[0:self.input_w]),]
        
        # DUMMY input_b interface
        comb += [self.input_b.ready.eq(self.input_a.accepted())]
    
        with m.FSM() as fsm:
            
            with m.State("IDLE"):
            
                comb += [self.input_a.ready.eq(self.output.accepted() | ~self.output.valid),
                         mac.clr.eq(1),
                         mac.clken.eq(0),]
            
                with m.If(self.input_a.accepted()):
                    m.next = "BUSY"
                    sync += [tmp_input_a.eq(Cat(*self.input_a.flat)), #self.input_a.data),
                             tmp_input_b.eq(Cat(*self.input_b.flat)), #Cat(*self.input_b)),
                             counter.eq(0),]
            
                with m.If(self.output.accepted()):
                    sync += self.output.valid.eq(0)
            
            with m.State("BUSY"):
            
                comb += [self.input_a.ready.eq(0),
                         mac.clr.eq(0),
                         mac.clken.eq(1),]
            
                sync += [tmp_input_b.eq(tmp_input_b >> self.input_w),
                         tmp_input_a.eq(tmp_input_a >> self.input_w),]
            
                with m.If(mac.valid_o):
                    sync += counter.eq(counter + 1)
                    with m.If(counter == self.n_inputs - 1):
                        m.next = "IDLE"
                        sync += [self.output.data.eq(mac.output),
                                 self.output.valid.eq(1),]

        return m
