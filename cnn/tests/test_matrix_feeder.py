from nmigen_cocotb import run
from cnn.matrix_feeder import MatrixFeeder
from cnn.tests.interfaces import MatrixStreamDriver, StreamDriver
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


@cocotb.coroutine
def init_test(dut):
    dut.rst <= 1
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)

def get_pixel(buffer, x, y, row_length):
    return buffer[row_length * y + x]

def check_monitors_data(buff_in, buff_out, width, height, N, invert=False):
    input_image = np.reshape(buff_in, (height, width))
    for i, output in enumerate(buff_out):
        output_image = np.reshape(output, (N, N))
        idx_x = i % (width + 1 - N)
        idx_y = int(i / (width + 1 - N))
        expected_submatrix = input_image[idx_y:idx_y+N, idx_x:idx_x+N]
        if invert:
            expected_submatrix = expected_submatrix[::-1, ::-1]
        assert (output_image == expected_submatrix).all(), f'output[{i}]: (x,y)={(idx_x,idx_y)}\n{output_image}\n!=\n{expected_submatrix}'


@cocotb.coroutine
def check_data(dut, N, height, width, invert=False, burps_in=False, burps_out=False, dummy=0):

    yield init_test(dut)

    m_axis = StreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = MatrixStreamDriver(dut, name='output_', clock=dut.clk, shape=(N,N))
    data_w = len(dut.input__data)
    m_axis.init_master()
    s_axis.init_slave()
    yield RisingEdge(dut.clk)

    image_size = width * height
    wr_data = wr_b = [int(x % (2**data_w-1)) for x in range(image_size)]
    expected_output_length = (width + 1 - N) * (height + 1 - N)

    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    cocotb.fork(m_axis.send(wr_data, burps_in))

    yield s_axis.recv(burps=burps_out)

    while len(s_axis.buffer) < expected_output_length:
        yield RisingEdge(dut.clk)

    dut._log.debug(f'Buffer in length: {len(m_axis.buffer)}.')
    dut._log.debug(f'Buffer out length: {len(s_axis.buffer)}.')
    assert len(m_axis.buffer) == len(wr_data), f'{len(m_axis.buffer)} != {len(wr_data)}'
    assert len(s_axis.buffer) == expected_output_length, f'{len(s_axis.buffer)} != {expected_output_length}'
    
    check_monitors_data(buff_in=m_axis.buffer, buff_out=s_axis.buffer,
                        width=width, height=height, N=N, invert=invert)


try:
    running_cocotb = True
    N = int(os.environ['coco_param_N'], 10)
    height = int(os.environ['coco_param_height'], 10)
    width = int(os.environ['coco_param_width'], 10)
    invert = int(os.environ['coco_param_invert'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('N', [N])
    tf_test_data.add_option('height', [height])
    tf_test_data.add_option('width', [width])
    tf_test_data.add_option('invert', [invert])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("data_w, height, width, N, invert", [(8, 5, 5, 3, False),
                                                               (8, 5, 5, 3, True),
                                                               ])
def test_matrix_feeder(data_w, height, width, N, invert):
    os.environ['coco_param_N'] = str(N)
    os.environ['coco_param_height'] = str(height)
    os.environ['coco_param_width'] = str(width)
    os.environ['coco_param_invert'] = str(int(invert))
    core = MatrixFeeder(data_w=data_w,
                        input_shape=(height, width),
                        N=N,
                        invert=invert)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_matrix_feeder_i{data_w}_h{height}_w{width}_N{N}_invert{invert}.vcd')
    run(core, 'cnn.tests.test_matrix_feeder', ports=ports, vcd_file=vcd_file)
