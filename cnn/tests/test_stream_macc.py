from nmigen_cocotb import run
from cnn.stream_macc import StreamMacc
from cnn.tests.utils import vcd_only_if_env
from cnn.tests.interfaces import SignedStreamDriver

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


class ROM():
    _generator = {
        'random': random.getrandbits,
        'limit': lambda width: 2**(width-1),
    }

    def __init__(self, dut, width, depth, profile):
        assert profile in self._generator
        self.dut = dut
        self.memory = [self._generator[profile](width) for _ in range(depth)]
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

def check_output(buff_in, coeff, buff_out, shift=0):
    assert len(buff_in) == len(coeff), (
        f'{len(buff_in)} != {len(coeff)}')
    assert len(buff_out) == 1, f'{len(buff_out)} != 1'
    acc = sum([a * b for a, b in zip(buff_in, coeff)])
    assert (acc >> shift) == buff_out[0], f'{acc} != {buff_out[0]}'


@cocotb.coroutine
def check_data(dut, burps_in=False, burps_out=False, dummy=0, profile='random'):
    width_a = len(dut.input__data)
    width_b = len(dut.r_data)
    width_out = len(dut.output__data)
    width_acc = len(dut.accumulator)
    shift = width_acc - width_out
    
    prod_req_bits = width_a + width_b
    # accum_req_bits = prod_req_bits + int(ceil(log2(test_size)))
    max_test_size = 2 ** (width_acc - prod_req_bits)

    test_size = min(128, max_test_size)
    rom = ROM(dut, width=width_b, depth=test_size, profile=profile)
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
    
    if profile == 'random':
        data_in = [random.getrandbits(width_a) for _ in range(test_size)]
    elif profile == 'limit':
        data_in = [2**(width_a-1) for _ in range(test_size)]

    cocotb.fork(m_axis.send(data_in, burps_in))
    yield s_axis.recv(test_size, burps_out)
    
    check_output(m_axis.buffer, rom.buffer, s_axis.buffer, shift=shift)


@cocotb.coroutine
def check_multiple(dut, burps_in=False, burps_out=False, dummy=0):
    
    width_a = len(dut.input__data)
    width_b = len(dut.r_data)
    width_out = len(dut.output__data)
    width_acc = len(dut.accumulator)
    shift = width_acc - width_out

    prod_req_bits = width_a + width_b
    max_test_size = 2 ** (width_acc - prod_req_bits)

    test_size = min(8, max_test_size)
    rom = ROM(dut, width=width_b, depth=test_size, profile='random')
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
    
    check_output(m_axis.buffer, rom.buffer, s_axis.buffer, shift=shift)


tf_test_random = TF(check_data)
tf_test_random.add_option('burps_in', [False, True])
tf_test_random.add_option('burps_out', [False, True])
tf_test_random.add_option('dummy', [0] * 5)
tf_test_random.add_option('profile', ['random'])
tf_test_random.generate_tests(postfix='_random')

tf_test_limit = TF(check_data)
tf_test_limit.add_option('profile', ['limit'])
tf_test_limit.generate_tests(postfix='_limit')

tf_test_multiple = TF(check_multiple)
tf_test_multiple.add_option('burps_in', [False, True])
tf_test_multiple.add_option('burps_out', [False, True])
tf_test_multiple.add_option('dummy', [0] * 5)
tf_test_multiple.generate_tests()


@pytest.mark.parametrize("args, kwargs", [
    ([], {'width_i': 8, 'width_c': 9}),
    ([], {'width_i': 8, 'width_c': 9, 'width_acc': 19}),
    ([], {'width_i': 8, 'width_c': 9, 'width_acc': 20, 'shift': 3}),
])
def test_stream_macc(args, kwargs):
    core = StreamMacc(*args, **kwargs)
    ports = core.get_ports()
    iw = len(core.input.data)
    cw = len(core.r_data)
    aw = len(core.accumulator)
    ow = len(core.output.data)
    vcd_file = vcd_only_if_env(f'./test_stream_macc_i{iw}_c{cw}_a{aw}_w{ow}.vcd')
    run(core, 'cnn.tests.test_stream_macc', ports=ports, vcd_file=vcd_file)