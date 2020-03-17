from nmigen import *
from cnn.utils import required_bits
from math import ceil, log2

class PipelinedTreeAdderStage(Elaboratable):
    def __init__(self, input_w, output_w, num_inputs, n):
        self.input_w = input_w
        self.output_w = output_w
        self.num_inputs = ceil(num_inputs / 2) * 2
        self.num_outputs = ceil(self.num_inputs / 2)
        self.inputs = [Signal(signed(self.input_w), name=n+'_input_'+str(i)) for i in range(self.num_inputs)]
        self.outputs = [Signal(signed(self.output_w), name=n+'_output_'+str(i)) for i in range(self.num_outputs)]
        self.clken = Signal()
        self.valid_i = Signal()
        self.valid_o = Signal()

    def get_ports(self):
        ports = []
        ports += [self.clken, self.valid_i, self.valid_o]
        ports += [p for p in self.inputs]
        ports += [p for p in self.outputs]
        return ports

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb
        
        with m.If(self.clken):
            sync += self.valid_o.eq(self.valid_i)
            for i, output in enumerate(self.outputs):
                sync += output.eq(self.inputs[int(2*i)] + self.inputs[int(2*i + 1)])
        with m.Else():
            sync += self.valid_o.eq(0)
            for i, output in enumerate(self.outputs):
                sync += output.eq(0)

        return m


class PipelinedTreeAdder(Elaboratable):
    def __init__(self, input_w, stages):
        self.input_w = input_w
        self.stages = stages
        self.output_w = self._required_output_bits(stages - 1)
        self.num_inputs = 2**(stages)
        self.inputs = [Signal(signed(self.input_w), name='input_' + str(i)) for i in range(self.num_inputs)]
        self.output = Signal(signed(self.output_w))
        self.clken = Signal()
        self.valid_i = Signal()
        self.valid_o = Signal()

    def get_ports(self):
        ports = []
        ports += [self.clken, self.valid_i, self.valid_o]
        ports += [p for p in self.inputs]
        ports += [self.output]
        return ports

    def _required_output_bits(self, stage):
        assert stage in range(self.stages)
        worst_value = -2**(self.input_w - 1)
        width_in = self.input_w
        for s in range(self.stages):
            worst_value *= 2
            if s == stage:
                return required_bits(worst_value)

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb
        
        tree_adder_stages = []

        input_w = self.input_w
        for stage_num in range(self.stages):
            output_w = self._required_output_bits(stage_num)
            stage = PipelinedTreeAdderStage(input_w, output_w, 2**(self.stages - stage_num), n='S'+str(stage_num))
            m.submodules['tree_adder_' + str(stage_num)] = stage
            tree_adder_stages.append(stage)
            x = tree_adder_stages[stage_num]
            input_w = output_w
            comb += stage.clken.eq(self.clken)

        comb += tree_adder_stages[0].valid_i.eq(self.valid_i)
        for i in range(len(tree_adder_stages[0].inputs)):
            comb += tree_adder_stages[0].inputs[i].eq(self.inputs[i])

        for stage_num in range(1, self.stages):
            first_stage = tree_adder_stages[stage_num-1]
            second_stage = tree_adder_stages[stage_num]
            comb += second_stage.valid_i.eq(first_stage.valid_o)
            for i in range(first_stage.num_outputs):
                comb += second_stage.inputs[i].eq(first_stage.outputs[i])

        comb += [self.valid_o.eq(tree_adder_stages[self.stages-1].valid_o),
                 self.output.eq(tree_adder_stages[self.stages-1].outputs[0]),
                ]

        return m
