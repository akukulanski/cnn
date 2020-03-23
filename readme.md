
# CNN

Convolutional Neural Network

Implementing a CNN in a Lattice ICE40HX4K.

To do:

* [x] MAC description
* [x] MAC test
* [ ] MAC synthesis (timing report)
* [x] Pipelined tree adder description
* [x] Pipelined tree adder test
* [ ] Pipelined tree adder synthesis
* [x] Dot product description
* [x] Dot product test
* [ ] Dot product synthesis (timing report)
* [ ] Dot product array block description
* [ ] Dot product array block test
* [ ] Dot product array block synthesis (timing report)
* [ ] Convolution 3x3 description
* [ ] Convolution 3x3 test
* [ ] Convolution 3x3 synthesis (timing report)
* [ ] Convolution NxN
* [ ] UART interface
* [ ] PC: Python Uart Tx/Rx
* [ ] Sigmoid? Softmax?
* [ ] Convolution Layer NxN * M
* [ ] CNN


### Requirements

* [nmigen](https://github.com/m-labs/nmigen) v0.1
* [yosys](https://github.com/YosysHQ/yosys) v0.9+
* [cocotb](https://github.com/cocotb/cocotb)
* [icarus verilog v10.1](https://github.com/akukulanski/nmigen-cocotb) (reported problems with v10.2+)
* [nmigen-cocotb](https://github.com/akukulanski/nmigen-cocotb)

### Testing

```bash
python3 -m pytest -vs cores/tests
```