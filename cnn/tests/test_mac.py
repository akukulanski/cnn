from nmigen_cocotb import run
from cnn.mac import MAC
from cnn.tests.utils import vcd_only_if_env
import pytest
import random
from math import ceil
import numpy as np

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
def input_monitor(dut, buff_in):
    while True:
        yield RisingEdge(dut.clk)
        if dut.clken.value.integer:
            buff_in.append((dut.input_a.value.signed_integer,
                            dut.input_b.value.signed_integer))

@cocotb.coroutine
def output_monitor(dut, buff_out):
    while True:
        yield RisingEdge(dut.clk)
        if dut.valid_o.value.integer:
            buff_out.append(dut.output.value.signed_integer)

def check_output(buff_in, buff_out):
    last = 0
    for (a, b), o in zip(buff_in, buff_out):
        assert o == last + a * b, f'{o} == {last} + {a} * {b}'
        last += a * b


@cocotb.coroutine
def init_test(dut):
    dut.input_a <= 0
    dut.input_b <= 0
    dut.clr <= 0
    dut.clken <= 0
    dut.rst <= 1
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def check_data(dut):

    width_in = len(dut.input_a)
    width_out = len(dut.output)

    yield init_test(dut)
    
    buff_in = []
    buff_out = []
    cocotb.fork(input_monitor(dut, buff_in))
    cocotb.fork(output_monitor(dut, buff_out))
    
    dut.clken <= 1
    for  _ in range(100):
        dut.input_a <= random.getrandbits(width_in)
        dut.input_b <= random.getrandbits(width_in)
        yield RisingEdge(dut.clk)

    yield RisingEdge(dut.clk)

    check_output(buff_in, buff_out)


tf_test_data = TF(check_data)
tf_test_data.generate_tests()

@pytest.mark.parametrize("input_w, output_w", [(8, 24),])
def test_mac(input_w, output_w):
    core = MAC(input_w=input_w,
               output_w=output_w)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_mac_i{input_w}_o{output_w}.vcd')
    run(core, 'cnn.tests.test_mac', ports=ports, vcd_file=vcd_file)