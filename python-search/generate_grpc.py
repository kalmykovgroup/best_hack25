"""
Скрипт для генерации Python кода из .proto файла
Запустите: python generate_grpc.py
"""
import subprocess
import sys
import io

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def generate():
    print("Генерация gRPC Python файлов из geocode.proto...")

    try:
        subprocess.run([
            sys.executable, "-m", "grpc_tools.protoc",
            "-I.",
            "--python_out=.",
            "--grpc_python_out=.",
            "geocode.proto"
        ], check=True)

        print("Файлы успешно сгенерированы:")
        print("   - geocode_pb2.py")
        print("   - geocode_pb2_grpc.py")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при генерации: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generate()
