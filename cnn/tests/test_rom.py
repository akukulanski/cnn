from nmigen_cocotb import run
from cnn.rom import CircularROM

import pytest
import random
import os
import numpy as np

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass

mem_init = list(range(10, 138))
CLK_PERIOD = 10

def create_clock(dut):
    cocotb.fork(Clock(dut.clk, CLK_PERIOD, 'ns').start())    

@cocotb.coroutine
def reset(dut):
    dut.restart <= 0
    dut.r_en <= 0
    dut.rst <= 1
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0

@cocotb.coroutine
def read_and_check(dut, burps):
    expected = 2 * mem_init[:depth]
    
    while len(expected):
        r_en = random.randint(0, 1) if burps else 1
        dut.r_en <= r_en
        yield RisingEdge(dut.clk)
        if dut.r_en.value.integer and dut.r_rdy.value.integer:
            exp = expected.pop(0)
            got = dut.r_data.value.integer
            assert got == exp, f'{got} != {exp}'

@cocotb.coroutine
def check_data(dut, burps=False, dummy=0):

    create_clock(dut)
    yield reset(dut)
    
    while not dut.r_rdy.value.integer:
        yield RisingEdge(dut.r_rdy)

    yield read_and_check(dut, burps)


@cocotb.coroutine
def check_restart(dut, burps=False, dummy=0):
    
    create_clock(dut)
    yield reset(dut)
    
    # random state
    for i in range(3 * depth):
        r_en = random.randint(0, 1)
        dut.r_en <= r_en
        yield RisingEdge(dut.clk)
    
    # back to a known state
    dut.restart <= 1
    yield RisingEdge(dut.clk)
    dut.restart <= 0
    
    yield read_and_check(dut, burps=burps)


try:
    running_cocotb = True
    depth = int(os.environ['cocotb_param_depth'], 10)
except KeyError:
    running_cocotb = False

if running_cocotb:
    tf_data = TF(check_data)
    tf_data.add_option('burps', [False, True])
    tf_data.add_option('dummy', [0]*5)
    tf_data.generate_tests()

    tf_restart = TF(check_restart)
    tf_restart.add_option('burps', [False, True])
    tf_restart.add_option('dummy', [0]*5)
    tf_restart.generate_tests()


@pytest.mark.parametrize(
    "width, depth", [
    (8, 8),
    ])
def test_core(width, depth):
    core = CircularROM(width=width,
                       init=mem_init[:depth])
    os.environ['cocotb_param_depth'] = str(depth)
    ports = core.get_ports()
    run(core, 'cnn.tests.test_rom', ports=ports, vcd_file=f'./test_rom_w{width}_d{depth}.vcd')

