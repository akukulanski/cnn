from nmigen import *
from cnn.stream_wrapper import StreamWrapper
from cnn.interfaces import DataStream, MatrixStream
from cnn.tree_operations import TreeHighestUnsigned


def TreeHighestUnsignedWrapped(width_i, n_stages, reg_in, reg_out):
    core = TreeHighestUnsigned(width_i=width_i, n_stages=n_stages,
                       reg_in=reg_in, reg_out=reg_out)
    latency = core.latency
    n_inputs = len(core.inputs)
    input_stream = MatrixStream(width_i, shape=(n_inputs,), direction='sink', name='input')
    output_stream = DataStream(core.output.width, direction='source', name='output')
    input_map = {}
    for i in range(n_inputs):
        input_map['data_' + str(i)] = core.inputs[i].name
    return StreamWrapper(wrapped_core=core,
                         input_stream=input_stream,
                         output_stream=output_stream,
                         input_map=input_map,
                         output_map={'data': 'output'},
                         latency=latency)
