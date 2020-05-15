from nmigen_cocotb import run
from cnn.convolution import Convolution
from cnn.tests.interfaces import MatrixStreamDriver, StreamDriver
from cnn.tests.utils import vcd_only_if_env, int_from_twos_comp
import cnn.matrix as mat
import pytest
import numpy as np
import os
from scipy import signal

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass

CLK_PERIOD_BASE = 100


def parse_buffer(buff_in, width, height, input_w):
    buff = [int_from_twos_comp(x, input_w) for x in buff_in]
    return np.reshape(buff, (height, width))


def check_monitors_data(coeff, buff_in, buff_out, width, height, N, input_w, output_w):
    input_image = parse_buffer(buff_in, width, height, input_w)
    input_coeff = parse_buffer(mat.flatten(coeff), N, N, input_w)
    output_image = parse_buffer(buff_out, width + 1 - N, height + 1 - N, output_w)
    expected_output = signal.convolve2d(input_image, input_coeff[::-1,::-1], mode='valid')
    assert (output_image == expected_output).all(), (
        f'\n{output_image}\n!=\n{expected_output}\n')


@cocotb.coroutine
def init_test(dut):
    dut.rst <= 1
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def check_data(dut, N, width, height=5, n_cores=1, burps_in=False, burps_out=False, dummy=0):

    yield init_test(dut)

    m_axis_coeff = MatrixStreamDriver(dut, name='coeff_', clock=dut.clk, shape=(N,N))
    m_axis = StreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = StreamDriver(dut, name='output_', clock=dut.clk)
    input_w = len(dut.input__data)
    output_w = len(dut.output__data)
    
    m_axis.init_master()
    m_axis_coeff.init_master()
    s_axis.init_slave()
    yield RisingEdge(dut.clk)

    image_size = width * height
    wr_data = wr_b = [int(x % (2**input_w-1)) for x in range(image_size)]
    expected_output_length = (width + 1 - N) * (height + 1 - N)

    coeff = m_axis_coeff._get_random_data()
    m_axis_coeff.write(coeff)

    dut._log.info(f'coeff={coeff}')

    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    cocotb.fork(s_axis.recv(expected_output_length, burps_out))

    yield m_axis.send(wr_data, burps_in)

    while len(s_axis.buffer) < expected_output_length:
        yield RisingEdge(dut.clk)

    dut._log.info(f'Buffer in length: {len(m_axis.buffer)}.')
    dut._log.info(f'Buffer out length: {len(s_axis.buffer)}.')
    assert len(m_axis.buffer) == len(wr_data), f'{len(m_axis.buffer)} != {len(wr_data)}'
    assert len(s_axis.buffer) == expected_output_length, f'{len(s_axis.buffer)} != {expected_output_length}'
    
    check_monitors_data(coeff=coeff, buff_in=m_axis.buffer, buff_out=s_axis.buffer,
                        width=width, height=height, N=N, input_w=input_w, output_w=output_w)


try:
    running_cocotb = True
    N = int(os.environ['coco_param_N'], 10)
    width = int(os.environ['coco_param_image_w'], 10)
    n_cores = int(os.environ['coco_param_n_cores'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('N', [N])
    tf_test_data.add_option('width', [width])
    tf_test_data.add_option('height', [5, 25])
    tf_test_data.add_option('n_cores', [n_cores])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("input_w, height, width, N, n_cores", [(8, 5, 5, 3, 9),
                                                                (8, 25, 5, 3, 9),
                                                                (8, 5, 5, 3, 1),
                                                                (8, 25, 5, 3, 1),
                                                            ])
def test_convolution(input_w, height, width, N, n_cores):
    os.environ['coco_param_N'] = str(N)
    os.environ['coco_param_height'] = str(height)
    os.environ['coco_param_width'] = str(width)
    os.environ['coco_param_n_cores'] = str(int(n_cores))
    core = Convolution(input_w=input_w,
                       input_shape=(height, width),
                       N=N,
                       n_cores=n_cores)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_convolution_i{input_w}_h{height}_w{width}_N{N}_n{n_cores}.vcd')
    run(core, 'cnn.tests.test_convolution', ports=ports, vcd_file=vcd_file)
