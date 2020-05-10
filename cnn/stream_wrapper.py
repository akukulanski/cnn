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


    def __init__(self, wrapped_core, input_stream, output_stream, max_latency, input_map={}, output_map={}, clken='clken'):
        """
        wrapped_core    object (instance of the core to be wrapped)
        input_stream    input stream instance
        output_stream   output stream instance
        max_latency     latency of the core being wrapped. Ensure this value is
                        equal or greater to the latency of the core.
        input_map       dictionary to map the wrapped core data ports to the input stream (not necessary if the names match)
        output_map      dictionary to map the wrapped core data ports to the output stream (not necessary if the names match)
        clken           name of the clken signal of the wrapped core.
        """
        self.wrapped_core = wrapped_core
        self.input = input_stream
        self.output = output_stream
        self.max_latency = max_latency
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

    @property
    def input_w(self):
        return sum([len(x) for x in self.input.data_ports()])
    
    @property
    def output_w(self):
        return sum([len(x) for x in self.output.data_ports()])

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

        # Wrapped core
        m.submodules.wrapped_core = wrapped_core = self.wrapped_core

        # control signals
        clken = Signal()
        latency_counter = Signal(range(self.max_latency))

        for core_field, stream_field in zip(self.get_wrapped_output_ports(), self.output.data_ports()):
            comb += stream_field.eq(core_field)

        with m.FSM() as fsm:

            with m.State("NORMAL"):
                comb += [self.wrapped_clken.eq(self.input.accepted() & self.output.accepted()),
                         self.output.valid.eq(self.input.valid),
                         self.output.last.eq(0),
                         self.input.ready.eq(self.output.ready),
                        ]
                #comb += [core_field.eq(stream_field) for core_field, stream_field in zip(self.get_wrapped_input_ports(), self.input.data_ports())],
                for core_field, stream_field in zip(self.get_wrapped_input_ports(), self.input.data_ports()):
                    comb += core_field.eq(stream_field)
                with m.If(self.wrapped_clken & self.input.last):
                    sync += latency_counter.eq(0)
                    m.next = "LAST"

            with m.State("LAST"):
                comb += [self.wrapped_clken.eq(self.output.accepted()),
                         self.output.valid.eq(1),
                         self.output.last.eq(Mux(latency_counter == self.max_latency - 1, 1, 0)),
                         self.input.ready.eq(0),
                        ]
                # comb += [di.eq(0) for di in self.get_wrapped_input_ports()],
                for di in self.get_wrapped_input_ports():
                    comb += di.eq(0)
                
                with m.If(self.wrapped_clken):
                    sync += latency_counter.eq(latency_counter + 1)
                    with m.If(latency_counter == self.max_latency - 1):
                        m.next = "NORMAL"

        return m


class StreamWrapper_Fifo(StreamWrapper):

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        sync = m.d.sync

        # Input fifo
        m.submodules.fifo_in = fifo_in = SyncFIFOBuffered(width=self.input_w,
                                                          depth=4)

        # Wrapped core
        m.submodules.wrapped_core = wrapped_core = self.wrapped_core

        # Output fifo
        m.submodules.fifo_out= fifo_out = SyncFIFOBuffered(width=self.output_w + 1,
                                                          depth=4)

        # Last delay line
        last_delay_line = Array([Signal() for _ in range(self.max_latency)])

        # control signals
        clken = Signal()
        last_arrived = Signal()

        # input --> fifo_in
        comb += [fifo_in.w_en.eq(self.input.accepted()),
                fifo_in.w_data.eq(self.input.flatten()),
                 self.input.ready.eq(Mux(last_arrived, 0, fifo_in.w_rdy)),
                ]

        # core --> fifo_out
        comb += fifo_out.w_data[:-1].eq(Cat(*self.get_wrapped_output_ports()))
        comb += fifo_out.w_data[-1].eq(last_delay_line[-1])

        # fifo_out --> output
        comb += [self.output.valid.eq(fifo_out.r_rdy),
                 self.output.eq_from_flat(fifo_out.r_data[:-1]),
                 self.output.last.eq(fifo_out.r_data[-1]),
                 fifo_out.r_en.eq(self.output.accepted())
                ]

        # Dataflow control
        comb += [self.wrapped_clken.eq(clken),
                 fifo_in.r_en.eq(clken),
                 fifo_out.w_en.eq(clken),
                ]

        with m.If(self.input.accepted() & self.input.last):
            sync += last_arrived.eq(1)

        with m.FSM() as fsm:

            with m.State("DATA"):
                comb += clken.eq(fifo_in.r_rdy & fifo_out.w_rdy)
                comb += connect_flat2array(flat=fifo_in.r_data, array=self.get_wrapped_input_ports()),

                with m.If(fifo_in.level == 0):
                    with m.If(last_arrived):
                        sync += last_delay_line[0].eq(1)
                        m.next = "LAST"

            with m.State("LAST"):
                comb += [clken.eq(fifo_out.w_rdy)]
                comb += [di.eq(0) for di in self.get_wrapped_input_ports()]

                with m.If(clken):
                    sync += last_delay_line[0].eq(0)
                    sync += [nxt.eq(prv) for prv, nxt in zip(last_delay_line[0:-1], last_delay_line[1:])]
                    with m.If(last_delay_line[-1]):
                        sync += last_arrived.eq(0)
                        m.next = "DATA"

        return m