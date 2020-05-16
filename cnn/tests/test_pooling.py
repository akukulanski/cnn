from nmigen_cocotb import run
from cnn.pooling import Pooling
from cnn.tests.interfaces import StreamDriver
from cnn.tests.utils import vcd_only_if_env
import pytest
import numpy as np
import os
import random

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass


def get_expected_data(wr_data, input_shape, N, mode):
    input_h, input_w = input_shape[0], input_shape[1]
    assert len(wr_data) % input_w == 0, f'{wr_data} % {input_w} != 0'
    assert int(len(wr_data) / input_w == input_h), f'{wr_data} / {input_w} != {input_h}'
    if mode == 'highest':
        shaped_data = np.reshape(wr_data, (input_h, input_w))
        expected = []
        for h in range(0, input_h, N):
            for w in range(0, input_w, N):
                submatrix = shaped_data[h:h+N, w:w+N]
                expected.append(max(submatrix.flatten()))
        return expected
    else:
        raise RuntimeError(f'mode {mode} is not implemented!')
    return


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
def check_data(dut, height, width, N, mode, burps_in=False, burps_out=False, dummy=0):

    m_axis = StreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = StreamDriver(dut, name='output_', clock=dut.clk)
    data_w = len(dut.input__data)

    create_clock(dut)
    m_axis.init_master()
    s_axis.init_slave()
    yield reset(dut)

    input_shape = (height, width)
    input_img_size = height * width
    output_shape = [int(x/N) for x in input_shape]

    wr_data = [random.getrandbits(data_w) for _ in range(input_img_size)]
    expected = get_expected_data(wr_data, input_shape, N, mode)
    
    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    
    send_thread = cocotb.fork(m_axis.send(wr_data, burps=burps_in))
    rd_data = yield s_axis.recv(burps=burps_out)
    yield send_thread.join()

    assert len(m_axis.buffer) == input_img_size, f'{len(m_axis.buffer)} != {input_img_size}'
    assert len(s_axis.buffer) == len(expected), f'{len(s_axis.buffer)} != {len(expected)}'
    assert rd_data == expected, (
        f'\n{np.reshape(rd_data, output_shape)}\n!=\n{np.reshape(expected, output_shape)}')


try:
    running_cocotb = True
    height = int(os.environ['coco_param_height'], 10)
    width = int(os.environ['coco_param_width'], 10)
    N = int(os.environ['coco_param_N'], 10)
    mode = os.environ['coco_param_mode']
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('height', [height])
    tf_test_data.add_option('width', [width])
    tf_test_data.add_option('N', [N])
    tf_test_data.add_option('mode', [mode])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.add_option('dummy', [0] * 5)
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("data_w, height, width, N, mode",
                        [(8, 6, 6, 2, 'highest'),
                         (8, 12, 15, 3, 'highest'),
                         (8, 15, 12, 3, 'highest'),
                        ])
def test_main(data_w, height, width, N, mode):
    os.environ['coco_param_height'] = str(height)
    os.environ['coco_param_width'] = str(width)
    os.environ['coco_param_N'] = str(N)
    os.environ['coco_param_mode'] = mode
    core = Pooling(data_w=data_w,
                   input_shape=(height, width),
                   N=N,
                   mode=mode)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_pooling_dw{data_w}_h{height}_w{width}_N{N}_m{mode}.vcd')
    run(core, 'cnn.tests.test_pooling', ports=ports, vcd_file=vcd_file)
