from nmigen import *
from nmigen.lib.fifo import SyncFIFOBuffered


def connect_flat2array(flat, array):
    assert sum([len(x) for x in array]) == len(flat), f'sum({[len(x) for x in array]}) != {len(flat)}'
    connections = []
    offset = 0
    for f in array:
        connections.append(f.eq(flat[offset:offset+len(f)]))
        offset += len(f)
    return connections

class StreamWrapper(Elaboratable):


    def __init__(self, wrapped_core, input_stream, output_stream, latency, input_map={}, output_map={}, clken='clken'):
        """
        wrapped_core    object (instance of the core to be wrapped)
        input_stream    input stream instance
        output_stream   output stream instance
        latency         latency of the core being wrapped.
        input_map       dictionary to map the wrapped core data ports to the input stream (not necessary if the names match)
        output_map      dictionary to map the wrapped core data ports to the output stream (not necessary if the names match)
        clken           name of the clken signal of the wrapped core.
        """
        self.wrapped_core = wrapped_core
        self.input = input_stream
        self.output = output_stream
        self.latency = latency
        self.input_map = input_map
        self.output_map = output_map
        self.clken_signal = clken
       
    def get_ports(self):
        ports = []
        ports += [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def __getattr__(self, key):
        if hasattr(self.wrapped_core, key):
            return getattr(self.wrapped_core, key)
        else:
            return object.__getattr__(self, key)

    @property
    def wrapped_clken(self):
        return getattr(self.wrapped_core, self.clken_signal)

    def get_wrapped_input_ports(self):
        try:
            return [getattr(self.wrapped_core, self.input_map[f[0]]) for f in self.input.DATA_FIELDS]
        except KeyError:
            return [getattr(self.wrapped_core, f[0]) for f in self.input.DATA_FIELDS]
    
    def get_wrapped_output_ports(self):
        try:
            return [getattr(self.wrapped_core, self.output_map[f[0]]) for f in self.output.DATA_FIELDS]
        except KeyError:
            return [getattr(self.wrapped_core, f[0]) for f in self.output.DATA_FIELDS]


    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        sync = m.d.sync

        m.submodules.wrapped_core = wrapped_core = self.wrapped_core

        clken = Signal()
        last_shift_reg = [Signal(1, name='sr_last_'+str(i)) for i in range(self.latency)]
        valid_shift_reg = [Signal(1, name='sr_valid_'+str(i)) for i in range(self.latency)]

        comb += clken.eq(self.output.ready | ~self.output.valid)
        comb += self.input.ready.eq(clken)
        comb += self.output.valid.eq(valid_shift_reg[-1])
        comb += self.output.last.eq(last_shift_reg[-1])
        comb += self.wrapped_clken.eq(clken)

        with m.If(clken):
            sync += valid_shift_reg[0].eq(self.input.accepted())
            for prv, nxt in zip(valid_shift_reg[:-1], valid_shift_reg[1:]):
                sync += nxt.eq(prv)
            sync += last_shift_reg[0].eq(self.input.accepted() & self.input.last)
            for prv, nxt in zip(last_shift_reg[:-1], last_shift_reg[1:]):
                sync += nxt.eq(prv)

        for core_field, stream_field in zip(self.get_wrapped_output_ports(), self.output.data_ports()):
            comb += stream_field.eq(core_field)

        for core_field, stream_field in zip(self.get_wrapped_input_ports(), self.input.data_ports()):
            comb += core_field.eq(stream_field)

        return m

