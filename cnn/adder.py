from nmigen import *


class TreeAdderStage(Elaboratable):

    def __init__(self, input_w, num_inputs, n, reg_in, reg_out):
        if num_inputs % 2 != 0:
            num_inputs += 1
        self.inputs = [Signal(signed(input_w), name=n+'_input_'+str(i)) for i in range(num_inputs)]
        self.outputs = [Signal(signed(input_w + 1), name=n+'_output_'+str(i)) for i in range(int(num_inputs / 2))]
        self.clken = Signal()
        self.reg_in = reg_in
        self.reg_out = reg_out

    def get_ports(self):
        ports = [self.clken] + self.inputs + self.outputs
        return ports

    @property
    def input_w(self):
        return len(self.inputs[0])

    @property
    def output_w(self):
        return len(self.outputs[0])

    @property
    def latency(self):
        return sum([int(b) for b in (self.reg_in, True, self.reg_out)])

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb
        
        i_dom = sync if self.reg_in else comb
        o_dom = sync if self.reg_out else comb

        input_r = [Signal(signed(self.input_w)) for _ in self.inputs]
        sum_r = [Signal(signed(self.output_w)) for _ in self.outputs]

        with m.If(self.clken):
            i_dom += [ir.eq(i) for ir, i in zip(input_r, self.inputs)]
            sync += [s.eq(input_r[int(2*i)] + input_r[int(2*i + 1)]) for i, s in enumerate(sum_r)]
            o_dom += [o.eq(sr) for o, sr in zip(self.outputs, sum_r)]

        return m


class TreeAdder(Elaboratable):

    def __init__(self, input_w, stages, *args, **kwargs):
        self.stages = stages
        self.inputs = [Signal(signed(input_w), name='input_' + str(i)) for i in range(2**(stages))]
        self.output = Signal(signed(input_w + stages))
        self.clken = Signal()
        self.args = args
        self.kwargs = kwargs
        self.tree_adder_stages = [TreeAdderStage(self.input_w+i,
                                            2**(self.stages-i),
                                            n='S'+str(i),
                                            *self.args,
                                            **self.kwargs
                                            ) for i in range(self.stages)]

    def get_ports(self):
        ports = [self.clken] + self.inputs + [self.output]
        return ports

    @property
    def input_w(self):
        return len(self.inputs[0])

    @property
    def output_w(self):
        return len(self.output)

    @property
    def num_inputs(self):
        return len(self.inputs)

    @property
    def latency(self):
        return sum(stage.latency for stage in self.tree_adder_stages)

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        tree_adder_stages = self.tree_adder_stages

        for i, stage in enumerate(tree_adder_stages):
            m.submodules['tree_adder_' + str(i)] = stage

        # Clock enable to all stages
        comb += [stage.clken.eq(self.clken) for stage in tree_adder_stages]

        # Connect input to first stage
        comb += [tree_adder_stages[0].inputs[i].eq(self.inputs[i]) for i in range(self.num_inputs)]

        # Pipelined adder stages
        for prv, nxt in zip(tree_adder_stages[0:-1], tree_adder_stages[1:]):
            comb += [nxt_i.eq(prv_o) for prv_o, nxt_i in zip(prv.outputs, nxt.inputs)]

        # Last stage to output
        comb += self.output.eq(tree_adder_stages[-1].outputs[0])

        return m