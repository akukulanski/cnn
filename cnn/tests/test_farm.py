from nmigen_cocotb import run
from cnn.farm import Farm
from cnn.tests.test_dot_product import check_data
from cnn.tests.utils import vcd_only_if_env
import pytest
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


try:
    string_to_tuple = lambda string: tuple([int(i) for i in string.replace('(', '').replace(')', '').split(',')])
    running_cocotb = True
    shape = string_to_tuple(os.environ['coco_param_shape'])
except KeyError as e:
    running_cocotb = False


if running_cocotb:
    # IMPORTED TEST FROM DOT_PRODUCT. SAME INTERFACES, SAME VALIDATION!
    tf_test_data = TF(check_data)
    tf_test_data.add_option('shape', [shape])
    tf_test_data.add_option('burps_in', [False, True])
    tf_test_data.add_option('burps_out', [False, True])
    tf_test_data.add_option('dummy', [0] * 5) # repeat 5 times
    tf_test_data.generate_tests()


@pytest.mark.parametrize("input_w, shape, n_cores", [(8, (4,2), 3)])
def test_farm(input_w, shape, n_cores):
    os.environ['coco_param_shape'] = str(shape)
    core = Farm(input_w=input_w,
                shape=shape,
                n_cores=n_cores)
    ports = core.get_ports()
    printable_shape = '_'.join([str(i) for i in shape])
    vcd_file = vcd_only_if_env(f'./test_farm_i{input_w}_shape{printable_shape}.vcd')
    run(core, 'cnn.tests.test_farm', ports=ports, vcd_file=vcd_file)
