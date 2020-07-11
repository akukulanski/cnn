
# CNN

This repository is an excuse to learn abount *Convolutional Neural Networks* by implementing one in FPGA.
The main goal is to learn, and to make good use of the tools I enjoy the most for digital design. These include
*nmigen*, *cocotb*, *yosys*, *icarus verilog*, *gtkwave*.

The status of this project is "very" **WIP**!


**To do (HDL):**

* [x] MACC: HDL + testbench (should be reimplemented to infer arch dependent dsp slices)
* [x] Pipelined tree adder: HDL + testbench
* [x] Dot product: HDL + testbench
* [x] Dot product array (*farm*): HDL + testbench
* [x] Row Fifo: HDL + testbench
* [x] MatrixFeeder: HDL + testbench
* [x] MatrixStream interface
* [x] Implement MatrixStream interface in existing cores
* [x] Convolution: HDL + testbench
* [x] Resizer (Padder & Cropper): HDL + testbench
* [ ] Convolution Layer
* [x] StreamWrapper for logic with clken
* [x] Pooling: HDL + testbench
* [x] ReLU
* [x] Ciruclar ROM: HDL + testbench
* [x] Stream MACC: HDL + testbench
* [ ] Sigmoid / Softmax
* [x] MLP node
* [ ] MLP layer
* [ ] CNN (Customizable integration of the cores above)
* [ ] UART interface to be able to run some tests in hw with a low-cost fpga (only as a proof of concept)
* [ ] PC: Python Uart Tx/Rx
* [ ] python2fpga

**To do (enhacements):**
* [ ] Paralell convolution by splitting input image

**To do (tools):**
* [x] Dockerfile
* [x] CI
* [ ] Python package
* [ ] Example of verilog generation

**To do (others):**
* [ ] Organize files, interfaces, etc. (this one will remain "undone" until a more stable design is reached)
* [ ] Document the cores, usage, etc.


### Requirements

There is a [dockerfile](./docker/dockerfile) available with all the required tools!

* [nmigen](https://github.com/nmigen/nmigen) (latest)
* [yosys](https://github.com/YosysHQ/yosys) (v0.9+, can use *yowasp-yosys*)
* [cocotb](https://github.com/cocotb/cocotb) (recommended 1.3.1+)
* [icarus verilog v10.1](hhttps://github.com/steveicarus/iverilog) (ensure cocotb doesn't run iverilog with `-g2012`.)
* [nmigen-cocotb@icarus-g2005](https://github.com/akukulanski/nmigen-cocotb/tree/icarus-g2005)
* pytest, pytest-repeat, pytest-timeout
* numpy
* scipy


### Testing

```bash
python3 -m pytest -vs cnn/ --log-cli-level info
```

### Intro to nn

* https://ujjwalkarn.me/2016/08/09/quick-intro-neural-networks/
* https://ujjwalkarn.me/2016/08/11/intuitive-explanation-convnets/
* https://medium.com/technologymadeeasy/the-best-explanation-of-convolutional-neural-networks-on-the-internet-fbb8b1ad5df8
