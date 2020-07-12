import os
import numpy as np

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


def pack(buffer, elements, element_width):
    """
        pack generator groups the buffer in packets of "elements"
        considering they have "element_width" bit length.

        args:
            elements: how many elements do you want to join
            element_with: which is the width of each element
        example:
            a = [0, 1, 2, 3, 4, 5]
            b = [p for p in pack(a, 3, 8)]
            result: [0x020100, 0x050403]
    """
    adicionales = (elements - (len(buffer) % elements)) % elements
    buff = buffer + [0]*adicionales
    for i in range(0, len(buff), elements):
        b = 0
        for j in range(elements):
            b = (b << element_width) + buff[i+elements-j-1]
        yield b

def unpack(buffer, elements, element_width):
    """
        unpack generator ungroups the buffer items in "elements"
        parts of "element_with" bit length.

        args:
            elements: In how many parts do you want to split an item.
            element_with: bit length of each part.
        example:
            a = [0x020100, 0x050403]
            b = [p for p in unpack(a, 3, 8)]
            result: [0, 1, 2, 3, 4, 5,]]
    """
    mask = (1 << element_width) - 1
    for b in buffer:
        for _ in range(elements):
            yield (b & mask)
            b = b >> element_width


def subfinder(mylist, pattern):
    sub = ','.join([str(x) for x in pattern]) # lo se, esto es horrible
    big = ','.join([str(x) for x in mylist])
    return sub in big 


vcd_only_if_env = lambda filename, env='WAVEFORM': filename if env in os.environ else None

"""
example usage:
    slice(dut.input__data, (8, 16))
    # returns input__data[8:16]
"""
slice_signal = lambda value, index: (value >> index[0]) & (2 ** (index[1] - index[0]) - 1)


def incremental_matrix(shape, size, max_value):
    n_elements = int(np.prod(shape))
    data = []
    count = 0
    for i in range(size):
        matrix = [x % max_value for x in range(count, count + n_elements)]
        data.append(matrix)
        count = (count + n_elements) % max_value
    return data