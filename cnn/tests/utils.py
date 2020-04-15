import os

def twos_comp_from_int(val, bits):
    """compute the 2's complement of int value val"""
    assert val >= -2**(bits-1)
    assert val < 2**(bits-1)
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val & (2**bits-1)                         # return positive value as is


def int_from_twos_comp(binary, bits):
    assert binary & (2**bits - 1) == binary
    val = binary & ~(2**(bits - 1)) 
    if binary & 2**(bits - 1): 
        val -= 2**(bits - 1) 
    return val


vcd_only_if_env = lambda filename, env='WAVEFORM': filename if env in os.environ else None

"""
example usage:
    slice(dut.input__TDATA, (8, 16))
    # returns input__TDATA[8:16]
"""
slice_signal = lambda value, index: (value >> index[0]) & (2 ** (index[1] - index[0]) - 1)