from nmigen import *
from cnn.utils.operations import _incr


class CircularROM(Elaboratable):

    def __init__(self, width, init):
        self.width = width
        self.depth = len(init)
        self.memory = Memory(width=width,
                             depth=self.depth,
                             init=init)
        self.r_en = Signal()
        self.r_rdy = Signal()
        self.r_data = Signal(width)
        self.restart = Signal()

    def get_ports(self):
        return [self.r_en, self.r_rdy, self.r_data, self.restart]

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        sync = m.d.sync

        m.submodules.rd_port = rd_port = self.memory.read_port(domain="sync")

        mem_data = Signal(self.width)

        mem_addr = Signal(range(self.depth))
        prev_addr = Signal(len(mem_addr))
        new_addr = Signal(len(mem_addr))

        delay_rdy = Signal()

        sync += prev_addr.eq(mem_addr)
        comb += new_addr.eq(_incr(prev_addr, self.depth))
        comb += mem_addr.eq(Mux(self.r_en & self.r_rdy, new_addr, prev_addr))
        comb += rd_port.addr.eq(mem_addr)

        with m.If(self.restart):
            sync += prev_addr.eq(0)
            sync += delay_rdy.eq(0)
            sync += self.r_rdy.eq(0)
        with m.Elif(~delay_rdy):
            sync += delay_rdy.eq(1)
        with m.Else():
            sync += self.r_rdy.eq(1)

        comb += mem_data.eq(rd_port.data)
        comb += self.r_data.eq(mem_data)

        return m