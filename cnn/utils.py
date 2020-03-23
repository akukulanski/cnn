from math import ceil, log2


def required_bits(value):
    if value > 0: 
        return ceil(1+log2(value + 1))
    else: 
        return ceil(log2(-value)+1) 



def _required_output_bits(stage):
    assert stage in range(self.stages)
    worst_value = -2**(self.input_w - 1)
    width_in = self.input_w
    for s in range(self.stages):
        worst_value *= 2
        if s == stage:
            return required_bits(worst_value)