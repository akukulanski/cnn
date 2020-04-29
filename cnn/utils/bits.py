from math import ceil, log2

def required_bits(value):
    if value > 0: 
        return ceil(1+log2(value + 1))
    else: 
        return ceil(log2(-value)+1)

