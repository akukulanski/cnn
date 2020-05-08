from nmigen import *


class TreeStage(Elaboratable):

    def __init__(self, input_w, num_inputs, n, reg_in, reg_out):
        assert num_inputs % 2 == 0
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

        _operation = self._operation

        with m.If(self.clken):
            i_dom += [ir.eq(i) for ir, i in zip(input_r, self.inputs)]
            sync += [s.eq(_operation.__call__(input_r[int(2*i)], input_r[int(2*i + 1)])) for i, s in enumerate(sum_r)]
            o_dom += [o.eq(sr) for o, sr in zip(self.outputs, sum_r)]

        return m


class TreeOperation(Elaboratable):
    _operation = None

    def __init__(self, input_w, n_stages, *args, **kwargs):
        class _Stage(TreeStage):
            _operation = self._operation

        self.n_stages = n_stages
        self.inputs = [Signal(signed(input_w), name='input_' + str(i)) for i in range(2**(n_stages))]
        self.output = Signal(signed(input_w + n_stages))
        self.clken = Signal()
        self.args = args
        self.kwargs = kwargs
        self.stages = [_Stage(self.input_w+i,
                              2**(self.n_stages-i),
                              n='S'+str(i),
                              *self.args,
                              **self.kwargs) for i in range(self.n_stages)]

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
        return sum(stage.latency for stage in self.stages)

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        stages = self.stages

        for i, stage in enumerate(stages):
            m.submodules['tree_oper_' + str(i)] = stage

        # Clock enable to all stages
        comb += [stage.clken.eq(self.clken) for stage in stages]

        # Connect input to first stage
        comb += [stages[0].inputs[i].eq(self.inputs[i]) for i in range(self.num_inputs)]

        # Pipelined stages
        for prv, nxt in zip(stages[0:-1], stages[1:]):
            comb += [nxt_i.eq(prv_o) for prv_o, nxt_i in zip(prv.outputs, nxt.inputs)]

        # Last stage to output
        comb += self.output.eq(stages[-1].outputs[0])

        return m


class TreeAdder(TreeOperation):
    _operation = lambda self, a, b: a + b

class TreeHighest(TreeOperation):
    _operation = lambda self, a, b: Mux(a > b, a, b)

class TreeLowest(TreeOperation):
    _operation = lambda self, a, b: Mux(a < b, a, b)