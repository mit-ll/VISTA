FROM python:3.7

RUN apt-get update && apt-get install --yes build-essential flex bison
RUN wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz && tar xvf pbc-0.5.14.tar.gz && cd /pbc-0.5.14 && ./configure LDFLAGS="-lgmp" && make -j$(nproc) && make install && ldconfig
RUN git clone https://github.com/JHUISI/charm.git && cd /charm && git checkout bbb7e62c
RUN cd /charm && ./configure.sh && make && make install

WORKDIR /vista
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY vista vista/