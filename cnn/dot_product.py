from nmigen import *
from cnn.mac import MAC
from cnn.utils import required_bits
from cores_nmigen.interfaces import AxiStream

class DotProduct(Elaboratable):
    def __init__(self, input_w, n_inputs, output_w=None, allow_overflow=False):
        self.input_w = input_w
        self.n_inputs = n_inputs
        self.output_w = self._calculate_output_width() if output_w is None else output_w
        self._check_output_w(allow_overflow)
        self.input = AxiStream(width=self.input_w*self.n_inputs, direction='sink', name='input')
        self.coeff = [Signal(self.input_w, name='coeff_'+str(i)) for i in range(self.n_inputs)]
        self.output = AxiStream(self.output_w, direction='source', name='output')

    def get_ports(self):
        ports = []
        ports += [coeff for coeff in self.coeff]
        ports += [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def _calculate_output_width(self):
        worst_value = -2**(self.input_w - 1)
        worst_mult = worst_value ** 2
        worst_result = worst_mult * self.n_inputs
        return required_bits(worst_result)

    def _check_output_w(self, allow_overflow):
        min_outut_w = self._calculate_output_width()
        if self.output_w < min_outut_w:
            print(f'WARNING: output_w is {self.output_w}. Minimum output_w to guarantee no overflow is {min_outut_w}')
        if not allow_overflow:
            assert self.output_w >= min_outut_w, f'{self.output_w} < {min_outut_w}'

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        tmp_input = Signal(self.input_w * self.n_inputs)
        tmp_coeff = Signal(self.input_w * self.n_inputs)
        counter = Signal(range(self.n_inputs))

        m.submodules['mac'] = mac = MAC(input_w=self.input_w, output_w=self.output_w)

        comb += [mac.input_a.eq(tmp_input[0:self.input_w]),
                 mac.input_b.eq(tmp_coeff[0:self.input_w]),]

    
        with m.FSM() as fsm:
            
            with m.State("IDLE"):
            
                comb += [self.input.ready.eq(self.output.accepted() | ~self.output.valid),
                         mac.clr.eq(1),
                         mac.clken.eq(0),]
            
                with m.If(self.input.accepted()):
                    m.next = "BUSY"
                    sync += [tmp_input.eq(self.input.data),
                             tmp_coeff.eq(Cat(*self.coeff)),
                             counter.eq(0),]
            
                with m.If(self.output.accepted()):
                    sync += self.output.valid.eq(0)
            
            with m.State("BUSY"):
            
                comb += [self.input.ready.eq(0),
                         mac.clr.eq(0),
                         mac.clken.eq(1),]
            
                sync += [tmp_coeff.eq(tmp_coeff >> self.input_w),
                         tmp_input.eq(tmp_input >> self.input_w),]
            
                with m.If(mac.valid_o):
                    sync += counter.eq(counter + 1)
                    with m.If(counter == self.n_inputs - 1):
                        m.next = "IDLE"
                        sync += [self.output.data.eq(mac.output),
                                 self.output.valid.eq(1),]

        return m
