from nmigen_cocotb import run
from cnn.tests.utils import vcd_only_if_env, incremental_matrix
from cnn.tests.interfaces import MatrixStreamDriver
import pytest
import os

try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass

from nmigen import *
from cnn.interfaces import MatrixStream
class MatrixInterfaceBypass(Elaboratable):
    
    def __init__(self, width, shape):
        self.width = width
        self.shape = shape
        self.input = MatrixStream(width=width, shape=shape, direction='sink', name='input')
        self.output = MatrixStream(width=width, shape=shape, direction='source', name='output')

    def get_ports(self):
        ports = [self.input[f] for f in self.input.fields]
        ports += [self.output[f] for f in self.output.fields]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        dummy = Signal() # just to force the existence of a clock domain
        sync += dummy.eq(~dummy)

        comb += [self.output.valid.eq(self.input.valid),
                 self.output.last.eq(self.input.last),
                 self.input.ready.eq(self.output.ready),
                ]

        comb += self.output.connect_data_ports(self.input)

        #######################################################################
        #
        # > Alternative methods to connect dataports
        #
        # * Iterating through data_ports
        #
        # for data_i, data_o in zip(self.input.data_ports, self.output.data_ports):
        #     comb += data_o.eq(data_i)
        #
        #######################################################################

        return m

CLK_PERIOD_BASE = 100


@cocotb.coroutine
def init_test(dut):
    dut.rst <= 1
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def check_data(dut, shape, dummy=0):
    
    test_size = 20
    yield init_test(dut)

    m_axis = MatrixStreamDriver(dut, name='input_', clock=dut.clk, shape=shape)
    s_axis = MatrixStreamDriver(dut, name='output_', clock=dut.clk, shape=shape)
    m_axis.init_master()
    s_axis.init_slave()

    yield RisingEdge(dut.clk)

    width_i = m_axis.width
    wr_data = incremental_matrix(shape, test_size, 2**width_i - 1)
    expected_output_length = len(wr_data)

    cocotb.fork(m_axis.monitor())
    cocotb.fork(s_axis.monitor())
    cocotb.fork(s_axis.recv(expected_output_length, burps=False))

    yield m_axis.send(wr_data, burps=False)

    while len(s_axis.buffer) < len(m_axis.buffer):
        yield RisingEdge(dut.clk)

    dut._log.debug(f'Buffer in length: {len(m_axis.buffer)}.')
    dut._log.debug(f'Buffer out length: {len(s_axis.buffer)}.')
    
    assert len(s_axis.buffer) == expected_output_length, f'{len(s_axis.buffer)} != {expected_output_length}'
    assert m_axis.buffer == s_axis.buffer, f'{m_axis.buffer} == {s_axis.buffer}'


try:
    string_to_tuple = lambda string: tuple([int(i) for i in string.replace('(', '').replace(')', '').split(',')])
    running_cocotb = True
    shape = string_to_tuple(os.environ['coco_param_shape'])
except KeyError as e:
    running_cocotb = False

if running_cocotb:
    tf_test_data = TF(check_data)
    tf_test_data.add_option('shape', [shape])
    tf_test_data.generate_tests()


@pytest.mark.timeout(10)
@pytest.mark.parametrize("width, shape", [(8, (4,2)),
                                          (8, (4,3,2)),
                                         ])
def test_matrix_interface(width, shape):
    os.environ['coco_param_shape'] = str(shape)
    core = MatrixInterfaceBypass(width=width,
                                 shape=shape,
                                )
    ports = core.get_ports()
    printable_shape = '_'.join([str(i) for i in shape])
    vcd_file = vcd_only_if_env(f'./test_matrix_interface_i{width}_shape{printable_shape}.vcd')
    run(core, 'cnn.tests.test_matrix_interface', ports=ports, vcd_file=vcd_file)
