from nmigen_cocotb import run
from cnn.mlp_node import mlpNode
from cnn.tests.utils import vcd_only_if_env
from cnn.tests.interfaces import StreamDriver

import os
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

def get_rom(width, depth, seed=None):
    random.seed(seed)
    _min, _max = -2**(width-1), +2**(width-1)-1
    rom = [random.randint(_min, _max) for _ in range(depth)]
    return rom

@cocotb.coroutine
def reset(dut):
    dut.rst <= 1
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)

def check_output(buff_in, coeff, buff_out):
    assert n_frames == len(buff_in) / n_inputs, (
        f'{n_frames} != {len(buff_in)} / {n_inputs}')
    assert len(buff_in) + n_frames == len(coeff), (
        f'{len(buff_in)} + {n_frames} != {len(coeff)}')
    assert len(buff_out) == n_frames, (
        f'{len(buff_out)} != {n_frames}')
    n_rom = n_inputs + 1
    for i in range(n_frames):
        di = buff_in[i*n_inputs:(i+1)*n_inputs]
        co = coeff[i*n_rom:(i+1)*n_rom]
        acc = sum([a * b for a, b in zip(di, co)])
        acc += co[-1]
        assert acc == buff_out[i], f'{acc} != {buff_out[i]}'


@cocotb.coroutine
def check_data(dut, burps_in=False, burps_out=False, dummy=0):

    data_w = len(dut.input__data)
    coeff_w = len(dut.rom.r_data)
    output_w = len(dut.output__data)
    rom_init = get_rom(coeff_w, (n_inputs+1)*n_frames, seed=seed)
    
    test_size = n_inputs
    m_axis = SignedStreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = SignedStreamDriver(dut, name='output_', clock=dut.clk)

    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    m_axis.init_master()
    s_axis.init_slave()
    yield reset(dut)
    
    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())

    for i in range(n_frames):
        data_in = [random.getrandbits(data_w) for _ in range(test_size)]
        cocotb.fork(m_axis.send(data_in, burps_in))
        yield s_axis.recv(1, burps_out)
    
    check_output(m_axis.buffer, rom_init[:(n_inputs+1)*n_frames], s_axis.buffer)


try:
    running_cocotb = True
    n_inputs = int(os.environ['coco_param_n_inputs'], 10)
    n_frames = int(os.environ['coco_param_n_frames'], 10)
    seed = int(os.environ['coco_param_seed'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.add_option('dummy', [0] * 5)
    tf_test_data.generate_tests()


@pytest.mark.parametrize("data_w, weight_w, n_inputs, n_frames",
[
    (8, 8, 8, 1),
    (8, 8, 8, 2),
    (8, 8, 1000, 2),
])
def test_mlp_node(data_w, weight_w, n_inputs, n_frames):
    seed = random.randint(0, 99999)
    os.environ['coco_param_n_inputs'] = str(n_inputs)
    os.environ['coco_param_n_frames'] = str(n_frames)
    os.environ['coco_param_seed'] = str(seed)
    rom_init = get_rom(weight_w, (n_inputs+1)*n_frames, seed=seed)
    core = mlpNode(data_w=data_w,
                   weight_w=weight_w,
                   n_inputs=n_inputs,
                   rom_init=rom_init)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_mlp_node_d{data_w}_w{weight_w}_n{n_inputs}.vcd')
    run(core, 'cnn.tests.test_mlp_node', ports=ports, vcd_file=vcd_file)