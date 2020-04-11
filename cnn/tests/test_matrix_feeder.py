from nmigen_cocotb import run
from cnn.matrix_feeder import MatrixFeeder
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

class MatrixFeederTest():
    def __init__(self, dut, row_length):
        self.dut = dut
        self.row_length = row_length
        self.input_w = len(self.dut.input__TDATA)
        self.output_w = len(self.dut.output__TDATA)
        self.buff_in = []
        self.buff_out = []

    @property
    def N(self):
        return int((self.output_w / self.input_w)**0.5)

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

    def generate_incremental_image(self, height):
        limits = (-2**(self.input_w - 1), 2**(self.input_w - 1) - 1)
        return [int(i % limits[1]) for i in range(self.row_length * height)]

    def check_data(self):
        width, height = self.row_length, int(len(self.buff_in) / self.row_length)
        input_image = np.reshape(self.buff_in, (height, width))
        for i, output in enumerate(self.buff_out):
            matrix_output = np.reshape(list(unpack([output], self.N ** 2, self.input_w)), (self.N, self.N))
            idx_x = i % (width + 1 - self.N)
            idx_y = int(i / (width + 1 - self.N))
            expected_submatrix = input_image[idx_y:idx_y+self.N, idx_x:idx_x+self.N]
            assert (matrix_output == expected_submatrix).all(), f'output[{i}]: (x,y)={(idx_x,idx_y)}\n{matrix_output}\n!=\n{expected_submatrix}'


class AxiStreamInterface(AxiStreamDriver):

    @cocotb.coroutine
    def send(self, data, burps=False):
        data = list(data)
        while len(data):
            valid = 1
            if burps:
                valid = random.randint(0, 1)
            self.bus.TVALID <= valid
            if valid:
                self.bus.TDATA <= data[0]
            else:
                self.bus.TDATA <= random.randint(0, 2**len(self.bus.TDATA)-1)
            yield RisingEdge(self.clk)
            if self.accepted():
                data.pop(0)
        self.bus.TVALID <= 0

    @cocotb.coroutine
    def recv(self, n, burps=False):
        while n:
            if burps:
                ready = random.randint(0, 1)
            else:
                ready = 1
            self.bus.TREADY <= ready
            yield RisingEdge(self.clk)
            if self.accepted():
                n = n - 1
        self.bus.TREADY <= 0


@cocotb.coroutine
def check_data(dut, width, height, burps_in, burps_out, dummy=0):
    test_size = 20

    test = MatrixFeederTest(dut, width)
    yield test.init_test()

    m_axis = AxiStreamInterface(dut, name='input_', clock=dut.clk)
    s_axis = AxiStreamInterface(dut, name='output_', clock=dut.clk)
    
    wr_data = test.generate_incremental_image(height)
    expected_output_length = (width + 1 - test.N) * (height + 1 - test.N)

    cocotb.fork(test.input_monitor())
    cocotb.fork(test.output_monitor())
    cocotb.fork(s_axis.recv(expected_output_length, burps_out))

    yield m_axis.send(wr_data, burps_in)

    while len(test.buff_out) < expected_output_length:
        yield RisingEdge(dut.clk)

    dut._log.info(f'Buffer in length: {len(test.buff_in)}.')
    dut._log.info(f'Buffer out length: {len(test.buff_out)}.')
    assert len(test.buff_out) == expected_output_length, f'{len(test.buff_out)} != {expected_output_length}'

    # print debug data
    dut._log.debug(f'\ninput image:\n{np.reshape(wr_data, (width, height))}')
    for i, d in enumerate(test.buff_out):
        tmp = list(unpack([d], test.N ** 2, test.input_w))
        dut._log.debug(f'\noutput matrix #{i}: {tmp}\n{np.reshape(tmp, (test.N, test.N))}')

    test.check_data()


try:
    running_cocotb = True
    width = int(os.environ['coco_param_row_length'], 10)
    N = int(os.environ['coco_param_N'], 10)
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('width', [width])
    tf_test_data.add_option('height', [5])
    tf_test_data.add_option('burps_in', [False]) #[False, True])
    tf_test_data.add_option('burps_out', [False]) #[False, True])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("input_w, row_length, N, endianness", [(8, 5, 3, -1),
                                                                # (8, 5, 3, +1),
                                                               ])
def test_matrix_feeder(input_w, row_length, N, endianness):
    os.environ['coco_param_row_length'] = str(row_length)
    os.environ['coco_param_N'] = str(N)
    core = MatrixFeeder(input_w=input_w,
                        row_length=row_length,
                        N=N,
                        endianness=endianness)
    ports = core.get_ports()
    run(core, 'cnn.tests.test_matrix_feeder', ports=ports, vcd_file=f'./test_matrix_feeder_i{input_w}_rowlength{row_length}_N{N}.vcd')
