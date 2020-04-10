
# CNN

Convolutional Neural Network

Implementing a CNN in a Lattice ICE40HX4K.

To do:

* [x] MAC description
* [x] MAC test
* [x] Pipelined tree adder description
* [x] Pipelined tree adder test
* [x] Dot product description
* [x] Dot product test
* [x] Dot product array (*farm*) block description
* [x] Dot product array (*farm*) block test
* [x] Row Fifo block description
* [x] Row Fifo block test
* [ ] MatrixFeeder block description: STARTED, UNTESTED.
    - [ ] split files
* [ ] MatrixFeeder block test
* [ ] Convolution integration block description
* [ ] Convolution integration block test
* [ ] UART interface
* [ ] PC: Python Uart Tx/Rx
* [ ] Sigmoid? Softmax?
* [ ] Convolution Layer NxN * M
* [ ] CNN

Single core synthesis + timing report:
* [ ] MAC
* [ ] Pipelined tree adder
* [ ] Dot product
* [ ] Dot product array (*farm*)
* [ ] Row Fifo
* [ ] Matrix Feeder
* [ ] Convolution integration (3x3)
* [ ] 
* [ ] 


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