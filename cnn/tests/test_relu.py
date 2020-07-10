from nmigen_cocotb import run
from cnn.relu import Relu
from cnn.tests.interfaces import SignedStreamDriver as Driver
from cnn.tests.utils import vcd_only_if_env, int_from_twos_comp
import pytest
import numpy as np
import os
import random
from math import floor

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass


def calc_expected(width, wr_data, leak):
    expected = []
    for val in wr_data:
        if val >= 0:
            exp = val
        elif leak == 0:
            exp = 0
        else:
            exp = int(floor(val / 2**(width-leak)))
        expected.append(exp)
    return expected


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
def check_data(dut, leak, burps_in=False, burps_out=False, dummy=0):

    m_axis = Driver(dut, name='input_', clock=dut.clk)
    s_axis = Driver(dut, name='output_', clock=dut.clk)
    width = len(dut.input__data)

    create_clock(dut)
    m_axis.init_master()
    s_axis.init_slave()
    yield reset(dut)

    test_size = 50
    wr_data = [int_from_twos_comp(random.getrandbits(width), width) for _ in range(test_size)]
    
    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    
    send_thread = cocotb.fork(m_axis.send(wr_data, burps=burps_in))
    rd_data = yield s_axis.recv(burps=burps_out)

    expected = calc_expected(width, wr_data, leak)
    assert len(m_axis.buffer) == test_size, f'{len(m_axis.buffer)} != {test_size}'
    assert len(s_axis.buffer) == len(expected), f'{len(s_axis.buffer)} != {len(expected)}'
    assert rd_data == expected, f'\n{rd_data}\n!=\n{expected}'


try:
    running_cocotb = True
    leak = int(os.environ['coco_param_leak'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('leak', [leak])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("width, leak", [
    (8, 0),
    (8, 1),
    (8, 7),
    (8, 8),
])
def test_main(width, leak):
    os.environ['coco_param_leak'] = str(leak)
    core = Relu(width=width,
                leak=leak)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_relu_w{width}_l{leak}.vcd')
    run(core, 'cnn.tests.test_relu', ports=ports, vcd_file=vcd_file)
