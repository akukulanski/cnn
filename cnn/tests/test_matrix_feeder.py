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

    def generate_random_image(self, height):
        limits = (-2**(self.input_w - 1), 2**(self.input_w - 1) - 1)
        return [random.randint(limits[0], limits[1]) for _ in range(self.row_length * height)]

    def generate_incremental_image(self, height):
        limits = (-2**(self.input_w - 1), 2**(self.input_w - 1) - 1)
        return [int(i % limits[1]) for i in range(self.row_length * height)]

    def check_data(self, buff_in, buff_out):
        width, height = self.row_length, int(len(buff_in) / self.row_length)
        input_image = np.reshape(buff_in, (height, width))
        for i, output in enumerate(buff_out):
            matrix_output = np.reshape(list(unpack([output], self.N ** 2, self.input_w)), (self.N, self.N))
            idx_x = i % (width + 1 - self.N)
            idx_y = int(i / (width + 1 - self.N))
            expected_submatrix = input_image[idx_y:idx_y+self.N, idx_x:idx_x+self.N]
            assert (matrix_output == expected_submatrix).all(), f'output[{i}]: (x,y)={(idx_x,idx_y)}\n{matrix_output}\n!=\n{expected_submatrix}'


@cocotb.coroutine
def check_data(dut, width, height, burps_in, burps_out, dummy=0):
    test_size = 20

    test = MatrixFeederTest(dut, width)
    yield test.init_test()

    m_axis = AxiStreamDriver(dut, name='input_', clock=dut.clk)
    s_axis = AxiStreamDriver(dut, name='output_', clock=dut.clk)
    
    wr_data = test.generate_incremental_image(height)
    expected_output_length = (width + 1 - test.N) * (height + 1 - test.N)

    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    cocotb.fork(s_axis.recv(expected_output_length, burps_out))

    yield m_axis.send(wr_data, burps_in)

    while len(s_axis.buffer) < expected_output_length:
        yield RisingEdge(dut.clk)

    dut._log.info(f'Buffer in length: {len(m_axis.buffer)}.')
    dut._log.info(f'Buffer out length: {len(s_axis.buffer)}.')
    assert len(s_axis.buffer) == expected_output_length, f'{len(s_axis.buffer)} != {expected_output_length}'

    # print debug data
    dut._log.info(f'\ninput image:\n{np.reshape(wr_data, (width, height))}')
    for i, d in enumerate(s_axis.buffer):
        tmp = list(unpack([d], test.N ** 2, test.input_w))
        dut._log.info(f'\noutput matrix #{i}: {tmp}\n{np.reshape(tmp, (test.N, test.N))}')

    test.check_data(m_axis.buffer, s_axis.buffer)


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
    tf_test_data.add_option('burps_in', [False, True]) # TO DO: FIX. Test NO PASA con burps_in==True.
    tf_test_data.add_option('burps_out', [False, True])
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
