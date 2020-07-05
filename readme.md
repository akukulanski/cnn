
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
* [ ] MLP node
* [ ] MLP layer
* [ ] CNN (Customizable integration of the cores above)
* [ ] UART interface to be able to run some tests in hw with a low-cost fpga (only as a proof of concept)
* [ ] PC: Python Uart Tx/Rx
* [ ] python2fpga

**To do (enhacements):**
* [ ] Arbitrer to share dps resources
* [ ] Paralell convolution by splitting input image

**To do (tools):**
* [ ] Dockerfile (test!)
* [ ] CI
* [ ] Python package
* [ ] Example of verilog generation

**To do (others):**
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

### Intro to nn

* https://ujjwalkarn.me/2016/08/09/quick-intro-neural-networks/
* https://ujjwalkarn.me/2016/08/11/intuitive-explanation-convnets/
* https://medium.com/technologymadeeasy/the-best-explanation-of-convolutional-neural-networks-on-the-internet-fbb8b1ad5df8
