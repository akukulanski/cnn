from nmigen_cocotb import run
from cnn.mac import MAC
from cnn.tests.utils import twos_comp_from_int, int_from_twos_comp
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

class MacTest():
    def __init__(self, dut):
        self.dut = dut
        self.input_w = len(self.dut.input_a)
        self.output_w = len(self.dut.output)
        self.buff_in = []
        self.buff_out = []

    @property    
    def current_a(self):
        return self.dut.input_a.value.integer

    @property
    def current_b(self):
        return self.dut.input_b.value.integer

    @property
    def current_output(self):
        return self.dut.output.value.integer

    @property
    def current_valid_o(self):
        return self.dut.valid_o.value.integer

    @property
    def current_clken(self):
        return self.dut.clken.value.integer

    @cocotb.coroutine
    def input_monitor(self):
        while True:
            yield RisingEdge(self.dut.clk)
            if self.current_clken:
                self.buff_in.append((int_from_twos_comp(self.current_a, self.input_w), int_from_twos_comp(self.current_b, self.input_w)))

    @cocotb.coroutine
    def output_monitor(self):
        while True:
            yield RisingEdge(self.dut.clk)
            if self.current_valid_o:
                self.buff_out.append(int_from_twos_comp(self.current_output, self.output_w))

    def check_data(self):
        last = 0
        for (a, b), o in zip(self.buff_in, self.buff_out):
            assert o == last + a * b, f'{o} == {last} + {a} * {b}'
            last += a * b


def generate_pair(bits):
    a = random.randint(0, 2**bits - 1)
    b = random.randint(0, 2**bits - 1)
    return a, b


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
    test = MacTest(dut)

    yield init_test(dut)
    
    cocotb.fork(test.input_monitor())
    cocotb.fork(test.output_monitor())

    limits = (-2**(width_in - 1), 2**(width_in - 1) - 1)
    
    dut.clken <= 1
    for a, b in [(random.randint(*limits), random.randint(*limits)) for _ in range(100)]:
        dut.input_a <= twos_comp_from_int(a, width_in)
        dut.input_b <= twos_comp_from_int(b, width_in)
        yield RisingEdge(dut.clk)

    yield RisingEdge(dut.clk)

    test.check_data()


tf_test_data = TF(check_data)
# tf_test_data.add_option('multiple', [True, False])
tf_test_data.generate_tests()

@pytest.mark.parametrize("input_w, output_w", [(8, 24),])
def test_mac(input_w, output_w):
    core = MAC(input_w=input_w,
               output_w=output_w)
    ports = [core.input_a, core.input_b, core.clken, core.clr, core.output, core.valid_o]
    run(core, 'cnn.tests.test_mac', ports=ports, vcd_file=f'./test_mac_i{input_w}_o{output_w}.vcd')