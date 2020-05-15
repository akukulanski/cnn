from nmigen_cocotb import run
from cnn.tree_operations_wrapped import TreeHighestUnsignedWrapped
from cnn.tests.interfaces import StreamDriver, MatrixStreamDriver
from cnn.tests.utils import vcd_only_if_env
import pytest
import numpy as np
import os

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass

CLK_PERIOD_BASE = 100


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
def check_data(dut, N, burps_in=False, burps_out=False, dummy=0):

    test_size = 10
    m_axis = MatrixStreamDriver(dut, name='input_', clock=dut.clk, shape=(N,))
    s_axis = StreamDriver(dut, name='output_', clock=dut.clk)
    input_w = len(m_axis.get_element(m_axis.first_idx))
    output_w = len(dut.output__data)
    
    m_axis.init_master()
    s_axis.init_slave()
    create_clock(dut)
    yield reset(dut)

    wr_data = [m_axis._get_random_data() for _ in range(test_size)]
    expected = [max(x) for x in wr_data]

    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    
    cocotb.fork(m_axis.send(wr_data, burps=burps_in))
    rd = yield s_axis.recv(burps=burps_out)

    dut._log.info(f'Buffer in length: {len(m_axis.buffer)}.')
    dut._log.info(f'Buffer out length: {len(s_axis.buffer)}.')
    assert len(m_axis.buffer) == len(wr_data), f'{len(m_axis.buffer)} != {len(wr_data)}'
    assert len(s_axis.buffer) == len(expected), f'{len(s_axis.buffer)} != {len(expected)}'
    assert s_axis.buffer == expected, f'{s_axis.buffer}\n!=\n{expected}'

try:
    running_cocotb = True
    N = int(os.environ['coco_param_N'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('N', [N])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("input_w, n_stages, reg_in, reg_out", [(8, 1, True, True),
                                                                (8, 3, False, False),
                                                                (8, 3, True, False),
                                                                (8, 3, False, True),
                                                                (8, 3, True, True),])
def test_main(input_w, n_stages, reg_in, reg_out):
    core = TreeHighestUnsignedWrapped(input_w=input_w,
                                      n_stages=n_stages,
                                      reg_in=reg_in,
                                      reg_out=reg_out)
    N = len(core.inputs)
    os.environ['coco_param_N'] = str(N)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_highest_w{input_w}_s{n_stages}.vcd')
    run(core, 'cnn.tests.test_highest', ports=ports, vcd_file=vcd_file)
