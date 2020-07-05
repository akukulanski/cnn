from nmigen_cocotb import run
from cnn.stream_macc import MACC_AXIS
from cnn.tests.utils import vcd_only_if_env
from cnn.tests.interfaces import StreamDriver

import pytest
import random
import numpy as np

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass

CLK_PERIOD_BASE = 100
random.seed()

class SignedStreamDriver(StreamDriver):
    def read(self):
        return self.bus.data.value.signed_integer

class ROM():
    def __init__(self, dut, width, depth):
        self.dut = dut
        self.memory = [random.getrandbits(width) for _ in range(depth)]
        self.buffer = []

    def init(self):
        self.dut.r_rdy <= 0
        self.dut.r_data <= 0

    @cocotb.coroutine
    def run(self):
        while self.dut.rst.value.integer:
            yield RisingEdge(self.dut.clk)
        yield RisingEdge(self.dut.clk)
        self.dut.r_rdy <= 1
        i = 0
        while True:
            self.dut.r_data <= self.memory[i]
            yield RisingEdge(self.dut.clk)
            if self.dut.r_rdy.value.integer and self.dut.r_en.value.integer:
                self.buffer.append(self.dut.r_data.value.signed_integer)
                i += 1
                i %= len(self.memory)

@cocotb.coroutine
def reset(dut):
    dut.rst <= 1
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)

def check_output(buff_in, coeff, buff_out):
    assert len(buff_in) == len(coeff), (
        f'{len(buff_in)} != {len(coeff)}')
    assert len(buff_out) == 1, f'{len(buff_out)} != 1'
    acc = sum([a * b for a, b in zip(buff_in, coeff)])
    assert acc == buff_out[0], f'{acc} != {buff_out[0]}'


@cocotb.coroutine
def check_data(dut, burps_in=False, burps_out=False, dummy=0):
    width_a = len(dut.input__data)
    width_b = len(dut.r_data)
    width_out = len(dut.output__data)
    
    test_size = 128
    rom = ROM(dut, width=width_b, depth=test_size)
    m_axis = SignedStreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = SignedStreamDriver(dut, name='output_', clock=dut.clk)
    
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    m_axis.init_master()
    s_axis.init_slave()
    rom.init()
    yield reset(dut)
    
    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    cocotb.fork(rom.run())
    
    data_in = [random.getrandbits(width_a) for _ in range(test_size)]

    cocotb.fork(m_axis.send(data_in, burps_in))
    yield s_axis.recv(test_size, burps_out)
    
    check_output(m_axis.buffer, rom.buffer, s_axis.buffer)


@cocotb.coroutine
def check_multiple(dut, burps_in=False, burps_out=False, dummy=0):
    
    width_a = len(dut.input__data)
    width_b = len(dut.r_data)
    width_out = len(dut.output__data)
    
    test_size = 8
    rom = ROM(dut, width=width_b, depth=test_size)
    m_axis = SignedStreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = SignedStreamDriver(dut, name='output_', clock=dut.clk)
    
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    m_axis.init_master()
    s_axis.init_slave()
    rom.init()
    yield reset(dut)

    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    cocotb.fork(rom.run())

    r = [random.getrandbits(width_a) for _ in range(15)]
    yield m_axis.send(r, burps=burps_in)
    yield s_axis.recv(1, burps=burps_out)

    m_axis.buffer[:] = []
    s_axis.buffer[:] = []
    rom.buffer[:] = []
    data_in = [random.getrandbits(width_a) for _ in range(test_size)]

    cocotb.fork(m_axis.send(data_in, burps_in))
    yield s_axis.recv(test_size, burps_out)
    
    check_output(m_axis.buffer, rom.buffer, s_axis.buffer)


tf_test_data = TF(check_data)
tf_test_data.add_option('burps_in', [False, True])
tf_test_data.add_option('burps_out', [False, True])
tf_test_data.add_option('dummy', [0] * 5)
tf_test_data.generate_tests()

tf_test_multiple = TF(check_multiple)
tf_test_multiple.add_option('burps_in', [False, True])
tf_test_multiple.add_option('burps_out', [False, True])
tf_test_multiple.add_option('dummy', [0] * 5)
tf_test_multiple.generate_tests()

@pytest.mark.parametrize("input_w, coeff_w", [(8, 9),])
def test_stream_macc(input_w, coeff_w):
    core = MACC_AXIS(input_w=input_w,
                     coeff_w=coeff_w)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_stream_macc_wa{input_w}_wb{coeff_w}.vcd')
    run(core, 'cnn.tests.test_stream_macc', ports=ports, vcd_file=vcd_file)