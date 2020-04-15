from nmigen_cocotb import run
from cnn.dot_product import DotProduct
from cnn.tests.utils import int_from_twos_comp, vcd_only_if_env
import cnn.matrix as mat
from cnn.tests.interfaces import AxiStreamMatrixDriver
from cores_nmigen.test.interfaces import AxiStreamDriver
import pytest
import random
import numpy as np
import os

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
    from .interfaces import *
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

def incremental_matrix(shape, size, max_value):
    data = []
    count = 0
    for i in range(size):
        matrix = mat.create_empty_matrix(shape)
        for idx in mat.matrix_indexes(shape):
            mat.set_matrix_element(matrix, idx, count)
            count = (count + 1) % max_value
        data.append(matrix)
    return data

def check_monitors_data(input_a, input_b, output, input_w, output_w):
    for a, b, o in zip(input_a, input_b, output):
        parsed_a = [int_from_twos_comp(x, input_w) for x in mat.flatten(a)]
        parsed_b = [int_from_twos_comp(x, input_w) for x in mat.flatten(b)]
        parsed_o = int_from_twos_comp(o, output_w)
        expected_o = sum(np.multiply(parsed_a, parsed_b))
        assert parsed_o == expected_o, f'{parsed_o} == {expected_o}'

@cocotb.coroutine
def check_data(dut, shape, burps_in, burps_out, dummy=0):

    test_size = 20
    yield init_test(dut)

    m_axis_a = AxiStreamMatrixDriver(dut, name='input_a_', clock=dut.clk, shape=shape)
    m_axis_b = AxiStreamMatrixDriver(dut, name='input_b_', clock=dut.clk, shape=shape)
    s_axis = AxiStreamDriver(dut, name='output_', clock=dut.clk)
    m_axis_a.init_sink()
    m_axis_b.init_sink()
    s_axis.bus.TREADY <= 0 # s_axis.init_source()
    yield RisingEdge(dut.clk)

    input_w = len(m_axis_a.get_element(m_axis_a.first_idx))
    output_w = len(dut.output__TDATA)
    
    wr_a = [m_axis_a._get_random_data() for _ in range(test_size)]
    wr_b = incremental_matrix(shape, test_size, 2**input_w - 1)

    cocotb.fork(m_axis_a.monitor())
    cocotb.fork(m_axis_b.monitor())
    cocotb.fork(s_axis.monitor())
    
    cocotb.fork(m_axis_a.send(wr_a, burps_in))
    cocotb.fork(m_axis_b.send(wr_b, burps=False)) # Dummy interface!

    yield s_axis.recv(test_size, burps_out)

    dut._log.info(f'Tested {len(s_axis.buffer)} cases.')
    assert len(m_axis_a.buffer) == test_size, f'{len(m_axis_a.buffer)} == {test_size}'
    assert len(m_axis_b.buffer) == test_size, f'{len(m_axis_b.buffer)} == {test_size}'
    assert len(s_axis.buffer) == test_size, f'{len(s_axis.buffer)} == {test_size}'
    
    check_monitors_data(m_axis_a.buffer, m_axis_b.buffer, s_axis.buffer, input_w, output_w)


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

@pytest.mark.parametrize("input_w, shape", [(8, (4,2))])
def test_dot_product(input_w, shape):
    os.environ['coco_param_shape'] = str(shape)
    core = DotProduct(input_w=input_w,
                      shape=shape)
    ports = core.get_ports()
    printable_shape = '_'.join([str(i) for i in shape])
    vcd_file = vcd_only_if_env(f'./test_dot_product_i{input_w}_shape{printable_shape}.vcd')
    run(core, 'cnn.tests.test_dot_product', ports=ports, vcd_file=vcd_file)
