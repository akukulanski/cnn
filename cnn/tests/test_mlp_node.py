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

def check_output(buff_in, coeff, buff_out, shift=0):
    assert n_neurons == len(buff_in) / n_inputs, (
        f'{n_neurons} != {len(buff_in)} / {n_inputs}')
    assert len(buff_in) + n_neurons == len(coeff), (
        f'{len(buff_in)} + {n_neurons} != {len(coeff)}')
    assert len(buff_out) == n_neurons, (
        f'{len(buff_out)} != {n_neurons}')
    n_rom = n_inputs + 1
    for i in range(n_neurons):
        di = buff_in[i*n_inputs:(i+1)*n_inputs]
        co = coeff[i*n_rom:(i+1)*n_rom]
        acc = sum([a * b for a, b in zip(di, co)])
        acc += co[-1]
        assert (acc >> shift) == buff_out[i], f'{acc} != {buff_out[i]}'


@cocotb.coroutine
def check_data(dut, burps_in=False, burps_out=False, dummy=0):

    width_i = len(dut.input__data)
    width_w = len(dut.rom.r_data)
    output_w = len(dut.output__data)
    acc_w = len(dut.macc.accumulator)
    shift = acc_w - output_w
    rom_init = get_rom(width_w, (n_inputs+1)*n_neurons, seed=seed)
    
    test_size = n_inputs
    m_axis = SignedStreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = SignedStreamDriver(dut, name='output_', clock=dut.clk)

    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    m_axis.init_master()
    s_axis.init_slave()
    yield reset(dut)
    
    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())

    for i in range(n_neurons):
        data_in = [random.getrandbits(width_i) for _ in range(test_size)]
        cocotb.fork(m_axis.send(data_in, burps_in))
        yield s_axis.recv(1, burps_out)
    
    check_output(buff_in=m_axis.buffer,
                 coeff=rom_init[:(n_inputs+1)*n_neurons],
                 buff_out=s_axis.buffer,
                 shift=shift)


try:
    running_cocotb = True
    n_inputs = int(os.environ['coco_param_n_inputs'], 10)
    n_neurons = int(os.environ['coco_param_n_neurons'], 10)
    seed = int(os.environ['coco_param_seed'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.add_option('dummy', [0] * 5)
    tf_test_data.generate_tests()


@pytest.mark.parametrize("width_i, width_w, n_inputs, n_neurons",
[
    (8, 8, 8, 1),
    (8, 8, 8, 2),
    (8, 8, 1000, 2),
])
def test_mlp_node(width_i, width_w, n_inputs, n_neurons):
    seed = random.randint(0, 99999)
    os.environ['coco_param_n_inputs'] = str(n_inputs)
    os.environ['coco_param_n_neurons'] = str(n_neurons)
    os.environ['coco_param_seed'] = str(seed) # so from cocotb can generate same random data
    rom_init = get_rom(width_w, (n_inputs+1)*n_neurons, seed=seed)
    core = mlpNode(width_i=width_i,
                   width_w=width_w,
                   n_inputs=n_inputs,
                   rom_init=rom_init)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_mlp_node_d{width_i}_w{width_w}_n{n_inputs}_m{n_neurons}.vcd')
    run(core, 'cnn.tests.test_mlp_node', ports=ports, vcd_file=vcd_file)