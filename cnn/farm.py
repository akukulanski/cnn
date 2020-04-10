from nmigen import *
from cnn.dot_product import DotProduct
from cores_nmigen.interfaces import AxiStream

class Farm(Elaboratable):
    def __init__(self, input_w, n_inputs, n_cores):
        self.input_w = input_w
        self.n_inputs = n_inputs
        self.n_cores = n_cores
        self.output_w = DotProduct(input_w, n_inputs).output_w # dummy just to calculate
        self.input = AxiStream(width=self.input_w*self.n_inputs, direction='sink', name='input')
        self.coeff = [Signal(self.input_w, name='coeff_'+str(i)) for i in range(self.n_inputs)] # To do: unify both input interfaces.
        self.output = AxiStream(self.output_w, direction='source', name='output')
        self.cores = [DotProduct(input_w, n_inputs) for _ in range(n_cores)]

    def get_ports(self):
        ports = []
        ports += [coeff for coeff in self.coeff]
        ports += [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        current_core_sink = Signal(range(self.n_cores))
        current_core_source = Signal(range(self.n_cores))

        # is this necessary?
        # cores_input_array = Array([c.input for c in self.cores])
        # cores_output_array = Array([c.output for c in self.cores])

        # the farm input is the AXIS input interface of the current_core_sink
        # comb += self.input.connect(cores_input_array[current_core_sink]) # comb += self.input.connect(self.cores[current_core_sink].input) # is this allowed?
        # the farm output is the AXIs output interface of the current_core_source
        # comb += self.output.connect(cores_output_array[current_core_source]) # comb += self.output.connect(self.cores[current_core_source].output) # is this allowed?
        
        for i, core in enumerate(self.cores):
            m.submodules['core_' + str(i)] = core
            comb += [core.coeff[n].eq(self.coeff[n]) for n in range(self.n_inputs)] # same coefficients for everybody
            with m.If(current_core_sink == i):
                # comb += self.input.connect(core.input)
                comb += [core.input.valid.eq(self.input.valid),
                         core.input.data.eq(self.input.data),
                         self.input.ready.eq(core.input.ready),
                        ]
            with m.Else():
                comb += [core.input.valid.eq(0),
                         core.input.data.eq(0),
                        ]
            with m.If(current_core_source == i):
                # comb += self.output.connect(core.output)
                comb += [self.output.valid.eq(core.output.valid),
                         self.output.data.eq(core.output.data),
                         core.output.ready.eq(self.output.ready),
                        ]
            with m.Else():
                comb += [core.output.ready.eq(0),
                        ]
        
        with m.If(self.input.accepted()):
            with m.If(current_core_sink < self.n_cores - 1):
                sync += current_core_sink.eq(current_core_sink + 1)
            with m.Else():
                sync += current_core_sink.eq(0)

        with m.If(self.output.accepted()):
            with m.If(current_core_source < self.n_cores - 1):
                sync += current_core_source.eq(current_core_source + 1)
            with m.Else():
                sync += current_core_source.eq(0)

        return m