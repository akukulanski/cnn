
# CNN

This repository is an excuse to learn abount *Convolutional Neural Networks* by implementing one in FPGA.
The main goal is to learn, and to make good use of the tools I enjoy the most for digital design. These include
*nmigen*, *cocotb*, *yosys*, *icarus verilog*, *gtkwave*.


**To do (HDL):**

* [x] MACC HDL
* [x] MACC testbench
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
* [x] Convolution integration HDL
* [x] Convolution integration testbench
* [ ] Paralell convolution HDL
* [ ] Paralell convolution testbench
* [ ] MACC: facilitate integration of DSP primitives
* [ ] Sigmoid? Softmax?
* [ ] Convolution Layer NxN * M
* [ ] CNN
* [ ] UART interface
* [ ] PC: Python Uart Tx/Rx

Single core synthesis + timing report:
* [ ] MACC
* [ ] Pipelined tree adder
* [ ] Dot product
* [ ] Dot product array (*farm*)
* [ ] Row Fifo
* [ ] Matrix Feeder
* [ ] Convolution integration (3x3)
...

**To do (tools):**
* [ ] Python package
* [ ] Example of verilog generation
* [ ] Dockerfile
* [ ] CI

**TO DO (others):**
* [ ] Organize files, interfaces, etc. (this one will remain "undone" until a more stable design is reached)
* [ ] Document (at least a little!)


### Requirements

* [nmigen](https://github.com/m-labs/nmigen) v0.1
* [yosys](https://github.com/YosysHQ/yosys) v0.9+
* [cocotb](https://github.com/cocotb/cocotb)
* [icarus verilog v10.1](hhttps://github.com/steveicarus/iverilog) (reported problems with v10.2+)
* [nmigen-cocotb](https://github.com/akukulanski/nmigen-cocotb)

Aditional Python deps:
* pytest
* numpy
* scipy

### Testing

```bash
python3 -m pytest -vs cnn/
```