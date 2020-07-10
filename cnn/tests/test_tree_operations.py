from nmigen_cocotb import run
from cnn.tree_operations import TreeAdderSigned
from cnn.tests.utils import subfinder, vcd_only_if_env
import pytest
import random
from math import ceil, log2


try:
    import cocotb
    from cocotb.triggers import RisingEdge
    from cocotb.clock import Clock
    from cocotb.regression import TestFactory as TF
except:
    pass

CLK_PERIOD_BASE = 100
random.seed()


def num_inputs(dut):
    i = 0
    while hasattr(dut, 'input_' + str(i)):
        i += 1
    return i

def stages(dut):
    return int(ceil(log2(num_inputs(dut))))

def set_input(dut, idx, value):
    getattr(dut, 'input_' + str(idx)) <= value

def set_input_vector(dut, vector):
    for idx, value in enumerate(vector):
        set_input(dut, idx, value)

def signed_random(width):
    _min, _max = -2**(width-1), 2**(width-1)-1
    return random.randint(_min, _max)

@cocotb.coroutine
def send(dut, data):
    dut.clken <= 1
    for vector in data:
        set_input_vector(dut, vector)
        yield RisingEdge(dut.clk)

    for _ in range(stages(dut) + 10):
        yield RisingEdge(dut.clk)

    dut.clken <= 0

@cocotb.coroutine
def recv(dut):
    buff = []
    yield RisingEdge(dut.clk)
    while dut.clken.value.integer:
        buff.append(dut.output.value.signed_integer)
        yield RisingEdge(dut.clk)
    return buff

@cocotb.coroutine
def init_test(dut):
    for idx in range(num_inputs(dut)):
        set_input(dut, idx, 0)
    dut.clken <= 0
    dut.rst <= 1
    cocotb.fork(Clock(dut.clk, 10, 'ns').start())
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def check_data(dut, dummy=0):

    test_size = 100
    width_i = len(dut.input_0)
    output_w = len(dut.output)
    n_inputs = num_inputs(dut)

    yield init_test(dut)

    wr_data = []
    for _ in range(test_size):
        wr_data.append([signed_random(width_i) for _ in range(n_inputs)])
    expected = [sum(x) for x in wr_data]

    cocotb.fork(send(dut, wr_data))

    rd_data = yield recv(dut)

    assert len(rd_data) >= len(wr_data)
    assert subfinder(rd_data, expected), f'{expected} not in {rd_data}'


tf_test_data = TF(check_data)
tf_test_data.add_option('dummy', [0] * 5)
tf_test_data.generate_tests()

@pytest.mark.parametrize("width_i, stages", [(8, 4), (8, 2), (8, 1),])
def test_main(width_i, stages):
    core = TreeAdderSigned(width_i=width_i,
                           n_stages=stages,
                           reg_in=True, reg_out=True)
    ports = core.get_ports()
    vcd_file = vcd_only_if_env(f'./test_adder_i{width_i}_s{stages}.vcd')
    run(core, 'cnn.tests.test_tree_operations', ports=ports, vcd_file=vcd_file)
