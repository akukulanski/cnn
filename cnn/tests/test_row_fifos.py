from nmigen_cocotb import run
from cnn.row_fifos import RowFifos
from cnn.tests.utils import twos_comp_from_int, int_from_twos_comp, slice_signal
from cores_nmigen.test.interfaces import AxiStreamDriver
from cores_nmigen.test.utils import pack, unpack
import pytest
import random
from math import ceil, log2
import numpy as np
import os

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

class RowFifosTest():
    def __init__(self, dut, row_length):
        self.dut = dut
        self.row_length = row_length
        self.input_w = len(self.dut.input__TDATA)
        self.output_w = len(self.dut.output__TDATA)
        self.buff_in = []
        self.buff_out = []

    @property
    def N(self):
        return int(self.output_w / self.input_w)

    def get_output(self, idx):
        inputs = list(unpack([self.dut.output__TDATA.value.integer], self.N, self.input_w))
        return inputs[idx]

    @cocotb.coroutine
    def init_test(self):
        self.dut.input__TVALID <= 0
        self.dut.input__TLAST <= 0
        self.dut.input__TDATA <= 0
        self.dut.output__TREADY <= 0
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
                self.buff_in.append(self.dut.input__TDATA.value.integer)

    @cocotb.coroutine
    def output_monitor(self):
        while True:
            yield RisingEdge(self.dut.clk)
            if self.dut.output__TVALID.value.integer and self.dut.output__TREADY.value.integer:
                self.buff_out.append(self.dut.output__TDATA.value.integer)

    def generate_random_image(self, height):
        limits = (-2**(self.input_w - 1), 2**(self.input_w - 1) - 1)
        return [random.randint(limits[0], limits[1]) for _ in range(self.row_length * height)]

    def check_data(self, endianness):
        for i, output in enumerate(self.buff_out):
            for n in range(self.N):
                _n = n if endianness == -1 else self.N-1-n
                pixel = slice_signal(output, (self.input_w*n, self.input_w*(n+1)))
                x = i % self.row_length
                y = int(i / self.row_length) + _n
                # self.dut._log.warning(f'({i}): {pixel} == get_pixel({self.buff_in}, {x}, {y})')
                assert pixel == self.get_pixel(self.buff_in, x, y), f'{pixel} == get_pixel({self.buff_in}, {x}, {y})'

    def get_pixel(self, buffer, x, y):
        return buffer[self.row_length * y + x]


@cocotb.coroutine
def check_data(dut, width, height, endianness, burps_in, burps_out, dummy=0):
    test_size = 20

    test = RowFifosTest(dut, width)
    yield test.init_test()

    m_axis = AxiStreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = AxiStreamDriver(dut, name='output_', clock=dut.clk)
    
    wr_data = test.generate_random_image(height)
    expected_output_length = len(wr_data) - width * (test.N - 1)

    cocotb.fork(test.input_monitor())
    cocotb.fork(test.output_monitor())
    cocotb.fork(s_axis.recv(expected_output_length, burps_out))

    yield m_axis.send(wr_data, burps_in)

    while len(test.buff_out) < expected_output_length:
        yield RisingEdge(dut.clk)

    dut._log.info(f'Buffer in length: {len(test.buff_in)}.')
    dut._log.info(f'Buffer out length: {len(test.buff_out)}.')
    assert len(test.buff_out) == expected_output_length, f'{len(test.buff_out)} != {expected_output_length}'
    test.check_data(endianness=endianness)


try:
    running_cocotb = True
    N = int(os.environ['coco_param_N'], 10)
    width = int(os.environ['coco_param_row_length'], 10)
    endianness = int(os.environ['coco_param_endianness'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('width', [width])
    tf_test_data.add_option('height', [5])
    tf_test_data.add_option('endianness', [endianness])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("input_w, row_length, N, endianness", [(8, 5, 3, -1),
                                                                (8, 5, 3, +1),
                                                               ])
def test_row_fifos(input_w, row_length, N, endianness):
    os.environ['coco_param_N'] = str(N)
    os.environ['coco_param_row_length'] = str(row_length)
    os.environ['coco_param_endianness'] = str(endianness)
    core = RowFifos(input_w=input_w,
                    row_length=row_length,
                    N=N,
                    endianness=endianness)
    ports = core.get_ports()
    run(core, 'cnn.tests.test_row_fifos', ports=ports, vcd_file=f'./test_row_fifos_i{input_w}_rowlength{row_length}_N{N}.vcd')
