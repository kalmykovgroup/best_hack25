FROM python:3.11-slim

# System dependencies for geopandas, pyrosm, libpostal, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    libspatialindex-dev \
    libgeos-dev \
    libproj-dev proj-bin proj-data \
    gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


# Устанавливаем необходимые системные зависимости для сборки libpostal
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    git \
    && rm -rf /var/lib/apt/lists/*

# Скачиваем и устанавливаем libpostal
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
RUN pip install --no-cache-dir \
    grpcio grpcio-tools \
    pandas \
    geopandas \
    pyrosm \
    bm25s \
    postal \
    autocorrect

# Copy your gRPC code and generated proto stubs
# (make sure these files exist in your build context)
COPY grpc_server.py geocode_pb2.py geocode_pb2_grpc.py ./

# Copy OSM PBF (or mount as volume in docker run instead)
# You can remove this and mount with -v if you prefer
COPY 10-moscow.osm.pbf /data/10-moscow.osm.pbf

ENV PBF_PATH=/data/10-moscow.osm.pbf
ENV GRPC_PORT=50051

EXPOSE 50051

CMD ["python", "grpc_server.py"]
