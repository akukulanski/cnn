from nmigen import *
from cnn.utils.operations import _incr


class CircularROM(Elaboratable):
    _doc_ = """
    Circular ROM is what it's name says.

    Parameters
    ----------
    width : int
        Bit width of data in stream interface.

    init : list
        ROM initialization data. Implicitily determinates
        the memory depth.
    """

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

        rd_port = self.memory.read_port(domain="sync")
        m.submodules.rd_port = rd_port

        delay_rdy = Signal() # delays r_rdy after reset
        prev_addr = Signal.like(rd_port.addr)

        do_read = self.r_en & self.r_rdy
        next_addr = _incr(prev_addr, self.depth)

        comb += self.r_data.eq(rd_port.data)
        sync += prev_addr.eq(rd_port.addr)

        with m.If(do_read):
            comb += rd_port.addr.eq(next_addr)
        with m.Else():
            comb += rd_port.addr.eq(prev_addr)

        with m.If(self.restart):
            sync += prev_addr.eq(0)
            sync += delay_rdy.eq(0)
            sync += self.r_rdy.eq(0)
        with m.Elif(~delay_rdy):
            sync += delay_rdy.eq(1)
        with m.Else():
            sync += self.r_rdy.eq(1)

        return m