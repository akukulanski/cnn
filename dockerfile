FROM debian:buster as builder

RUN echo 'APT::Install-Recommends "0";\nAPT::Install-Suggests "0";' > /etc/apt/apt.conf.d/01norecommend && \
    apt-get update && \
    apt-get -y install build-essential \
                       clang \
                       bison \
                       flex \
                       libreadline-dev \
                       gawk \
                       tcl-dev \
                       libffi-dev \
                       git \
                       graphviz \
                       xdot \
                       pkg-config \
                       libboost-system-dev \
                       libboost-python-dev \
                       libboost-filesystem-dev \
                       zlib1g-dev \
                       python3 \
                       python3-pip \
                       python3-venv \
                       autoconf \
                       gperf && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PREFIX /opt/yosys
RUN git clone https://github.com/YosysHQ/yosys.git /yosys/ && \
    make -C /yosys/ -j$(nproc) && make -C /yosys/ install


####################################
# Second stage
####################################
FROM debian:buster-slim as final

RUN echo 'APT::Install-Recommends "0";\nAPT::Install-Suggests "0";' > /etc/apt/apt.conf.d/01norecommend && \
    apt-get update && \
    apt-get -y install \
        git \
        ssh \
        make \
        wget \
        build-essential\
        iputils-ping \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-setuptools \
        python3-tk \
        python3-wheel \
        iverilog \
        libftdi-dev \
        libtinfo5 && \
    apt-get autoremove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# https://github.com/YosysHQ/yosys/blob/master/Dockerfile
COPY --from=builder /opt/yosys /opt/yosys
ENV PATH /opt/yosys/bin:$PATH

RUN wget http://http.us.debian.org/debian/pool/main/i/iverilog/iverilog_10.1-0.1+b2_amd64.deb && \
    dpkg -i iverilog_10.1-0.1+b2_amd64.deb && \
    apt-get install -f && \
    dpkg -i iverilog_10.1-0.1+b2_amd64.deb && \
    apt-get autoremove && \
    apt-get clean && \
    rm -r iverilog_10.1-0.1+b2_amd64.deb
RUN iverilog -V | grep --color "Icarus Verilog version 10\.1"

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install ipython pytest numpy scipy cocotb==1.3.0 nmigen==0.1
RUN python3 -m pip install git+https://github.com/akukulanski/nmigen-cocotb.git

