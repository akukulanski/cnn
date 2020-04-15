
# CNN

Convolutional Neural Network

Implementing a CNN in a Lattice ICE40HX4K.

To do:

* [x] MAC HDL
* [x] MAC testbench
* [x] Pipelined tree adder HDL
* [x] Pipelined tree adder testbench
* [x] Dot product HDL
* [x] Dot product testbench
* [x] Dot product array (*farm*) HDL
* [x] Dot product array (*farm*) testbench
* [x] Row Fifo HDL
* [x] Row Fifo testbench
* [x] MatrixFeeder HDL.
* [x] MatrixFeeder testbench
* [x] AxiStreamMatrix interface
* [x] Implement AxiStreamMatrix interface in existing cores
* [ ] Convolution integration HDL
* [ ] Convolution integration testbench
* [ ] Paralell convolution HDL
* [ ] Paralell convolution testbench
* [ ] UART interface
* [ ] PC: Python Uart Tx/Rx
* [ ] Sigmoid? Softmax?
* [ ] Convolution Layer NxN * M
* [ ] CNN
* [ ] Organize files, interfaces.

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
* [icarus verilog v10.1](hhttps://github.com/steveicarus/iverilog) (reported problems with v10.2+)
* [nmigen-cocotb](https://github.com/akukulanski/nmigen-cocotb)

### Testing

```bash
python3 -m pytest -vs cores/tests
```