from nmigen_cocotb import run
from cnn.adder import PipelinedTreeAdder
from cnn.tests.utils import twos_comp_from_int, int_from_twos_comp
import pytest
import random
from math import ceil, log2
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

class AdderTest():
    def __init__(self, dut):
        self.dut = dut
        self.input_w = len(self.dut.input_0)
        self.output_w = len(self.dut.output)
        self.buff_in = []
        self.buff_out = []

    @property
    def num_inputs(self):
        i = 0
        while hasattr(self.dut, 'input_' + str(i)):
            i += 1
        return i
    
    @property
    def stages(self):
        return int(log2(self.num_inputs))

    def get_input(self, idx):
        return getattr(self.dut, 'input_' + str(idx)).value.integer

    def set_input(self, idx, value):
        getattr(self.dut, 'input_' + str(idx)) <= twos_comp_from_int(value, self.input_w)

    def set_input_vector(self, vector):
        for idx, value in enumerate(vector):
            self.set_input(idx, value)

    @property
    def valid_i(self):
        return self.dut.valid_i.value.integer
    
    @property
    def output(self):
        return self.dut.output.value.integer

    @property
    def valid_o(self):
        return self.dut.valid_o.value.integer

    @property
    def clken(self):
        return self.dut.clken.value.integer
    
    @cocotb.coroutine
    def init_test(self):
        self.set_input_vector([0] * self.num_inputs)
        for idx in range(self.num_inputs):
            self.set_input(idx, 0)
        self.dut.clken <= 0
        self.dut.valid_i <= 0
        self.dut.rst <= 1
        cocotb.fork(Clock(self.dut.clk, 10, 'ns').start())
        yield RisingEdge(self.dut.clk)
        self.dut.rst <= 0
        yield RisingEdge(self.dut.clk)

    @cocotb.coroutine
    def input_monitor(self):
        while True:
            yield RisingEdge(self.dut.clk)
            if self.clken and self.valid_i:
                tmp = []
                for idx in range(self.num_inputs):
                    tmp.append(int_from_twos_comp(self.get_input(idx), self.input_w))
                self.buff_in.append(tmp)

    @cocotb.coroutine
    def output_monitor(self):
        while True:
            yield RisingEdge(self.dut.clk)
            if self.clken and self.valid_o:
                self.buff_out.append(int_from_twos_comp(self.output, self.output_w))

    def generate_random_vector(self):
        limits = (-2**(self.input_w - 1), 2**(self.input_w - 1) - 1)
        tmp = []
        for _ in range(self.num_inputs):
            tmp.append(random.randint(limits[0], limits[1]))
        return tmp

    def check_data(self):
        for inputs, o in zip(self.buff_in, self.buff_out):
            assert o == sum(inputs), f'{o} == sum({inputs})'


@cocotb.coroutine
def check_data(dut):
    test_size = 100
    test = AdderTest(dut)
    yield test.init_test()

    cocotb.fork(test.input_monitor())
    cocotb.fork(test.output_monitor())

    dut.clken <= 1
    for vector in [test.generate_random_vector() for _ in range(test_size)]:
        test.set_input_vector(vector)
        dut.valid_i <= 1
        yield RisingEdge(dut.clk)
        dut.valid_i <= 0

    for _ in range(test.stages + 1):
        yield RisingEdge(dut.clk)

    dut.clken <= 0

    dut._log.info(f'Tested {len(test.buff_out)} cases.')
    assert len(test.buff_out) == test_size, f'{len(test.buff_out)} == {test_size}'
    assert len(test.buff_in) == len(test.buff_out), f'{len(test.buff_in)} == {len(test.buff_out)}'
    test.check_data()


tf_test_data = TF(check_data)
# tf_test_data.add_option('multiple', [True, False])
tf_test_data.generate_tests()

@pytest.mark.parametrize("input_w, stages", [(8, 4), (8, 2), (8, 1),])
def test_adder(input_w, stages):
    core = PipelinedTreeAdder(input_w=input_w,
                              stages=stages)
    ports = core.get_ports()
    run(core, 'cnn.tests.test_adder', ports=ports, vcd_file=f'./test_adder_i{input_w}_s{stages}.vcd')
