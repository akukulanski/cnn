from nmigen_cocotb import run
from cnn.resize import Padder, Cropper, Resizer
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


def create_clock(dut):
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())


def zero_init_master(driver):
    driver.bus.valid <= 0
    driver.bus.last <= 0
    driver.bus.data <= 0


def zero_init_slave(driver):
    driver.bus.ready <= 0


def get_expected_data(wr_data, input_shape, output_shape, fill_value):
    if (input_shape[0] <= output_shape[0]) and (input_shape[1] <= output_shape[1]):
        zeros = [fill_value for _ in range(output_shape[0] * output_shape[1])]
        result = np.reshape(zeros, output_shape)
        result[:input_shape[0], :input_shape[1]] = np.reshape(wr_data, input_shape)
    else:
        result = np.reshape(wr_data, input_shape)[:output_shape[0], :output_shape[1]]
    return [int(x) for x in result.flatten()]


@cocotb.coroutine
def reset(dut):
    dut.rst <= 1
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def check_data(dut, input_shape, output_shape, fill_value=0, burps_in=False, burps_out=False, dummy=0):

    m_axis = StreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = StreamDriver(dut, name='output_', clock=dut.clk)
    data_w = len(dut.input__data)

    create_clock(dut)
    zero_init_master(m_axis)
    zero_init_slave(s_axis)
    yield reset(dut)

    input_img_h, input_img_w = input_shape
    output_img_h, output_img_w = output_shape

    input_img_size = input_img_h * input_img_w
    output_img_size = output_img_h * output_img_w
    wr_data = [random.getrandbits(data_w) for _ in range(input_img_size)]
    expected = get_expected_data(wr_data, input_shape, output_shape, fill_value)
    
    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    send_thread = cocotb.fork(m_axis.send(wr_data))
    rd_data = yield s_axis.recv()
    yield send_thread.join()

    assert len(m_axis.buffer) == input_img_size, f'{len(m_axis.buffer)} != {input_img_size}'
    assert len(s_axis.buffer) == output_img_size, f'{len(s_axis.buffer)} != {output_img_size}'
    assert rd_data == expected, (
        f'\n{np.reshape(rd_data, output_shape)}\n!=\n{np.reshape(expected, output_shape)}')


try:
    running_cocotb = True
    ih = int(os.environ['coco_param_ih'], 10)
    iw = int(os.environ['coco_param_iw'], 10)
    oh = int(os.environ['coco_param_oh'], 10)
    ow = int(os.environ['coco_param_ow'], 10)
    fill_value = int(os.environ['coco_param_fill_value'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    input_shape = (ih, iw)
    output_shape = (oh, ow)
    tf_test_data = TF(check_data)
    tf_test_data.add_option('input_shape', [input_shape])
    tf_test_data.add_option('output_shape', [output_shape])
    tf_test_data.add_option('fill_value', [fill_value])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    # tf_test_data.add_option('dummy', [0])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("data_w, input_shape, output_shape, fill_value",
                        [(8, (3, 3), (6, 4), 0), # padding
                         (8, (3, 6), (7, 7), 0), # padding
                         (8, (3, 6), (7, 9), 0), # padding
                         (8, (3, 6), (9, 7), 0), # padding
                         (8, (5, 2), (5, 4), 0), # padding
                         (8, (5, 2), (7, 2), 1), # padding
                         (8, (5, 2), (5, 2), 0), # keep shape
                         (8, (6, 4), (3, 3), 0), # cropping
                         (8, (7, 7), (3, 6), 0), # cropping
                         (8, (7, 9), (3, 6), 0), # cropping
                         (8, (9, 7), (3, 6), 0), # cropping
                         (8, (5, 4), (5, 2), 0), # cropping
                         (8, (7, 2), (5, 2), 0), # cropping
                        ])
def test_main(data_w, input_shape, output_shape, fill_value):
    ih, iw = input_shape
    oh, ow = output_shape
    os.environ['coco_param_ih'] = str(ih)
    os.environ['coco_param_iw'] = str(iw)
    os.environ['coco_param_oh'] = str(oh)
    os.environ['coco_param_ow'] = str(ow)
    os.environ['coco_param_fill_value'] = str(fill_value)
    core = Resizer(data_w=data_w,
                   input_shape=input_shape,
                   output_shape=output_shape,
                   fill_value=fill_value)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_resizer_ih{ih}_iw{iw}_oh{oh}_ow{ow}_fill{fill_value}.vcd')
    run(core, 'cnn.tests.test_resizer', ports=ports, vcd_file=vcd_file)
