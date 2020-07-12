from nmigen_cocotb import run
from cnn.dot_product import DotProduct
from cnn.tests.utils import vcd_only_if_env, incremental_matrix
from cnn.tests.interfaces import SignedMatrixStreamDriver as MatrixDriver
from cnn.tests.interfaces import SignedStreamDriver as Driver
import pytest
import random
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
random.seed()


@cocotb.coroutine
def init_test(dut):
    dut.rst <= 1
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)

def check_monitors_data(input_a, input_b, output):
    for a, b, o in zip(input_a, input_b, output):
        expected_o = sum(np.multiply(a, b))
        assert o == expected_o, f'{o} == {expected_o}'

@cocotb.coroutine
def check_data(dut, shape, burps_in, burps_out, dummy=0):

    test_size = 20
    yield init_test(dut)

    m_axis_a = MatrixDriver(dut, name='input_a_', clock=dut.clk, shape=shape)
    m_axis_b = MatrixDriver(dut, name='input_b_', clock=dut.clk, shape=shape)
    s_axis = Driver(dut, name='output_', clock=dut.clk)
    m_axis_a.init_master()
    m_axis_b.init_master()
    s_axis.init_slave()
    yield RisingEdge(dut.clk)

    width_i = m_axis_a.width
    
    wr_a = [m_axis_a._get_random_data() for _ in range(test_size)]
    wr_b = incremental_matrix(shape, test_size, 2**width_i - 1)

    cocotb.fork(m_axis_a.monitor())
    cocotb.fork(m_axis_b.monitor())
    cocotb.fork(s_axis.monitor())
    
    cocotb.fork(m_axis_a.send(wr_a, burps_in))
    cocotb.fork(m_axis_b.send(wr_b, burps=False)) # Dummy interface!

    yield s_axis.recv(test_size, burps_out)

    dut._log.debug(f'Tested {len(s_axis.buffer)} cases.')
    assert len(m_axis_a.buffer) == test_size, f'{len(m_axis_a.buffer)} == {test_size}'
    assert len(m_axis_b.buffer) == test_size, f'{len(m_axis_b.buffer)} == {test_size}'
    assert len(s_axis.buffer) == test_size, f'{len(s_axis.buffer)} == {test_size}'
    
    check_monitors_data(m_axis_a.buffer, m_axis_b.buffer, s_axis.buffer)


try:
    string_to_tuple = lambda string: tuple([int(i) for i in string.replace('(', '').replace(')', '').split(',')])
    running_cocotb = True
    shape = string_to_tuple(os.environ['coco_param_shape'])
except KeyError as e:
    running_cocotb = False


if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('shape', [shape])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.add_option('dummy', [0] * 5) # repeat 5 times
    tf_test_data.generate_tests()

@pytest.mark.parametrize("width_i, shape", [(8, (4,2))])
def test_dot_product(width_i, shape):
    os.environ['coco_param_shape'] = str(shape)
    core = DotProduct(width_i=width_i,
                      shape=shape)
    ports = core.get_ports()
    printable_shape = '_'.join([str(i) for i in shape])
    vcd_file = vcd_only_if_env(f'./test_dot_product_i{width_i}_shape{printable_shape}.vcd')
    run(core, 'cnn.tests.test_dot_product', ports=ports, vcd_file=vcd_file)
