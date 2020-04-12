import numpy as np
import copy


def create_empty_matrix(shape):
    matrix = 0
    for i in shape[::-1]:
        matrix = [copy.deepcopy(matrix) for _ in range(i)]
    return matrix


def matrix_indexes(shape):
    return _recursive_iter(shape)


def get_matrix_element(matrix, indexes):
    tmp = matrix
    for idx in indexes:
        tmp = tmp[idx]
    return copy.deepcopy(tmp)


def set_matrix_element(matrix, indexes, value):
    tmp = matrix
    for idx in indexes[:-1]:
        tmp = tmp[idx]
    assert np.shape(tmp[indexes[-1]]) == np.shape(value), f'{np.shape(tmp[indexes[-1]])} = {np.shape(value)}'
    tmp[indexes[-1]] = copy.deepcopy(value)


def _recursive_iter(shape, prev_idx=()):
    for s in range(shape[0]):
        current_idx = (*prev_idx, s)
        if len(shape) == 1:
            yield current_idx
        else:
            yield from _recursive_iter(shape[1:], current_idx)


class Matrix(object):
    
    def __init__(self, shape=(1,)):
        self.shape = shape
        self.matrix = create_empty_matrix(shape)

    def _len(self, value):
        if hasattr(value, '__iter__'):
            return len(value)
        return 1

    def __iter__(self):
        return _recursive_iter(self.shape)

    def __getitem__(self, tup):
        if not hasattr(tup, '__iter__'):
            tup = (tup,)
        return self._get_value(tup)

    def __setitem__(self, tup, value):
        if not hasattr(tup, '__iter__'):
            tup = (tup,)
        return self._set_value(tup, value)

    def _get_value(self, indexes):
        tmp = self.matrix
        for idx in indexes:
            tmp = tmp[idx]
        return copy.deepcopy(tmp)

    def _set_value(self, indexes, value):
        tmp = self.matrix
        for idx in indexes[:-1]:
            tmp = tmp[idx]
        print(f'prev: {tmp[indexes[-1]]}\nnew: {value}')
        assert np.shape(tmp[indexes[-1]]) == np.shape(value), f'{np.shape(tmp[indexes[-1]])} = {np.shape(value)}'
        tmp[indexes[-1]] = copy.deepcopy(value)


# def linear2matrix(linear, shape)
#     # is this a reshape?
#     n_elements = np.prod(shape)
#     matrix = Matrix(shape)
#     for i, value in range(list_of_values):
#         indexes = [0] * len(shape)
#         for s in range(len(shape)):
#             indexes[s] = int(i / np.prod(shape[s+1::])) % shape[s]
#         # print(f'element #{i} <-- idx {indexes}')
#         # x = int(i / (shape[2] * shape[1])) % shape[0]
#         # y = int(i / shape[2]) % shape[1]
#         # z = i % shape[2]
#         matrix[indexes] = 