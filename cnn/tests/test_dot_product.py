from nmigen_cocotb import run
from cnn.dot_product import DotProduct
from cnn.tests.utils import twos_comp_from_int, int_from_twos_comp
from cores_nmigen.test.interfaces import AxiStreamDriver
from cores_nmigen.test.utils import pack, unpack
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

class DotProductTest():
    def __init__(self, dut):
        self.dut = dut
        self.input_w = int(len(self.dut.input__TDATA) / self.n_inputs)
        self.output_w = len(self.dut.output__TDATA)
        self.buff_in = []
        self.buff_coeffs = []
        self.buff_out = []

    @property
    def n_inputs(self):
        i = 0
        while hasattr(self.dut, 'coeff_' + str(i)):
            i += 1
        return i

    def get_input(self, idx):
        inputs = list(unpack([self.dut.input__TDATA.value.integer], self.n_inputs, self.input_w))
        return inputs[idx]
        # offset = self.input_w * idx
        # return self.dut.input__TDATA[offset:offset+self.input_w].value.integer

    def set_input_vector(self, vector):
        for idx, value in enumerate(vector):
            offset = self.input_w * idx
            self.dut.input__TDATA[offset:offset+self.input_w] <= twos_comp_from_int(value, self.input_w)

    def get_coeffs(self):
        return [int_from_twos_comp(getattr(self.dut, 'coeff_'+str(i)).value.integer, self.input_w) for i in range(self.n_inputs)]

    def set_coeffs(self, coeffs):
        for i in range(len(coeffs)):
            getattr(self.dut, 'coeff_'+str(i)) <= twos_comp_from_int(coeffs[i], self.input_w)

    @cocotb.coroutine
    def init_test(self):
        self.dut.input__TVALID <= 0
        self.dut.input__TLAST <= 0
        self.dut.input__TDATA <= 0
        self.dut.output__TREADY <= 0
        for i in range(self.n_inputs):
            getattr(self.dut, 'coeff_'+str(i)) <= 0
        self.dut.rst <= 1
        cocotb.fork(Clock(self.dut.clk, 10, 'ns').start())
        yield RisingEdge(self.dut.clk)
        self.dut.rst <= 0
        yield RisingEdge(self.dut.clk)

    @cocotb.coroutine
    def input_monitor(self):
        while True:
            yield RisingEdge(self.dut.clk)
            if self.dut.input__TVALID.value.integer and self.dut.input__TREADY.value.integer:
                tmp = []
                coeffs = self.get_coeffs()
                for idx in range(self.n_inputs):
                    tmp.append(int_from_twos_comp(self.get_input(idx), self.input_w))
                self.buff_in.append(tmp)
                self.buff_coeffs.append(coeffs)

    @cocotb.coroutine
    def output_monitor(self):
        while True:
            yield RisingEdge(self.dut.clk)
            if self.dut.output__TVALID.value.integer and self.dut.output__TREADY.value.integer:
                self.buff_out.append(int_from_twos_comp(self.dut.output__TDATA.value.integer, self.output_w))

    def generate_random_vector(self):
        limits = (-2**(self.input_w - 1), 2**(self.input_w - 1) - 1)
        tmp = []
        for _ in range(self.n_inputs):
            tmp.append(random.randint(limits[0], limits[1]))
        return tmp

    def check_data(self):
        for inputs, coeffs, o in zip(self.buff_in, self.buff_coeffs, self.buff_out):
            assert o == sum(np.multiply(inputs, coeffs)), f'{o} != {sum(np.multiply(inputs, coeffs))} (sum(np.multiply({inputs}, {coeffs})))'

    def flatten(self, vector):
        return list(pack(vector, self.n_inputs, self.input_w))[0]

@cocotb.coroutine
def check_data(dut, burps_in, burps_out, dummy=0):
    test_size = 20

    test = DotProductTest(dut)
    yield test.init_test()

    m_axis = AxiStreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = AxiStreamDriver(dut, name='output_', clock=dut.clk)
    
    coeffs = test.generate_random_vector()
    test.set_coeffs(coeffs)

    wr = [test.flatten(test.generate_random_vector()) for _ in range(test_size)]

    cocotb.fork(test.input_monitor())
    cocotb.fork(test.output_monitor())
    cocotb.fork(s_axis.recv(test_size, burps_out))

    yield m_axis.send(wr, burps_in)
    
    while len(test.buff_out) < test_size:
        yield RisingEdge(dut.clk)

    dut._log.info(f'Tested {len(test.buff_out)} cases.')
    assert len(test.buff_out) == test_size, f'{len(test.buff_out)} == {test_size}'
    assert len(test.buff_in) == len(test.buff_out), f'{len(test.buff_in)} == {len(test.buff_out)}'
    test.check_data()


tf_test_data = TF(check_data)
tf_test_data.add_option('burps_in', [False, True])
tf_test_data.add_option('burps_out', [False, True])
tf_test_data.add_option('dummy', [0] * 5) # repeat 5 times
tf_test_data.generate_tests()

@pytest.mark.parametrize("input_w, n_inputs", [(8, 4)])
def test_dot_product(input_w, n_inputs):
    core = DotProduct(input_w=input_w,
                      n_inputs=n_inputs)
    ports = core.get_ports()
    run(core, 'cnn.tests.test_dot_product', ports=ports, vcd_file=f'./test_dot_product_i{input_w}_o{core.output_w}_n{n_inputs}.vcd')
