#!/bin/bash
# Скрипт для генерации Python кода из proto файлов

python -m grpc_tools.protoc \
    -I./protos \
    --python_out=. \
    --grpc_python_out=. \
    ./protos/address_parser.proto

echo "Proto files generated successfully!"
