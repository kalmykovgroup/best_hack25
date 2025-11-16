FROM python:3.11-slim

# System dependencies for geopandas, pyrosm, libpostal
RUN apt-get update && apt-get install -y \
    build-essential \
    libspatialindex-dev \
    libgeos-dev \
    libproj-dev proj-bin proj-data \
    gdal-bin libgdal-dev \
    curl \
    autoconf \
    automake \
    libtool \
    pkg-config \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install and build libpostal
RUN git clone https://github.com/openvenues/libpostal /libpostal && \
    cd /libpostal && \
    ./bootstrap.sh && \
    ./configure --datadir=/usr/local/share/libpostal && \
    make -j4 && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /libpostal

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    grpcio \
    grpcio-tools \
    protobuf \
    pandas \
    geopandas \
    pyrosm \
    bm25s \
    postal \
    autocorrect

# Copy proto file and generate gRPC code
COPY geocode.proto ./
RUN python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    geocode.proto

# Copy application code
COPY grpc_server.py ./

# Copy OSM PBF file (you can also mount it as volume with -v)
COPY 10-moscow.osm.pbf /data/10-moscow.osm.pbf

# Environment variables
ENV PBF_PATH=/data/10-moscow.osm.pbf
ENV GRPC_PORT=50054
ENV PYTHONUNBUFFERED=1

EXPOSE 50054

CMD ["python", "grpc_server.py"]