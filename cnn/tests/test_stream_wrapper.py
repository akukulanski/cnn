from nmigen_cocotb import run
from nmigen import *
from cnn.stream_wrapper import StreamWrapper
from cnn.interfaces import DataStream
from cnn.tests.interfaces import StreamDriver

import pytest
import random
import os

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass


CLK_PERIOD = 10

class ExampleCore(Elaboratable):

    def __init__(self, width, latency):
        self.data_i = Signal(width)
        self.data_o = Signal(width)
        self.clken = Signal()
        self.latency = latency

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        sync = m.d.sync

        registers = Array([Signal(len(self.data_i), name='register_'+str(i)) for i in range(self.latency)])

        comb += self.data_o.eq(registers[-1])

        with m.If(self.clken):
            sync += registers[0].eq(self.data_i)
            sync += [nxt.eq(prv) for prv, nxt in zip(registers[:-1], registers[1:])]

        return m


def create_clock(dut):
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())


@cocotb.coroutine
def reset(dut):
    dut.rst <= 1
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def check_data(dut, burps_in=False, burps_out=False, dummy=0):
    
    test_size = 100
    data_w = len(dut.input__data)
    wr_data = [random.getrandbits(data_w) for _ in range(test_size)]
    expected = wr_data

    m_axis = StreamDriver(dut, 'input_', dut.clk)
    s_axis = StreamDriver(dut, 'output_', dut.clk)

    create_clock(dut)
    m_axis.init_master()
    s_axis.init_slave()
    yield reset(dut)

    cocotb.fork(m_axis.monitor())
    cocotb.fork(m_axis.send(wr_data, burps=burps_in))

    yield RisingEdge(dut.clk)

    rd_data = yield s_axis.recv(burps=burps_out)

    assert wr_data == m_axis.buffer, f'{wr_data} != {m_axis.buffer}'
    assert rd_data == expected, f'{expected}\n!=\n{rd_data}'


tf = TF(check_data)
tf.add_option('burps_in', [False, True])
tf.add_option('burps_out', [False, True])
tf.add_option('dummy', [0] * 5)
tf.generate_tests()


@pytest.mark.parametrize("latency", [1, 4, 5])
def test_main_wrapper(latency):
    core = StreamWrapper(wrapped_core=ExampleCore(16, latency),
                         input_stream=DataStream(16, direction='sink', name='input'),
                         output_stream=DataStream(16, direction='source', name='output'),
                         input_map={'data': 'data_i'},
                         output_map={'data': 'data_o'},
                         latency=latency)
    ports = core.get_ports()
    run(core, 'cnn.tests.test_stream_wrapper', ports=ports, vcd_file=f'./test_stream_wrapper.vcd')
