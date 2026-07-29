import socket
import json
import time
import os

sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 20777))

os.makedirs("packets", exist_ok=True)   # 确保目录存在
information=[]
while True:
    data, addr = sock.recvfrom(65535)
    # print(f"Received message: {data.decode()} from {addr}")
    # print(f"  Hex: {data.hex()}")
    # print(f"  Data: {data}")
    filename = f"packets/{int(time.time() * 1_000_000)}_{addr[1]}.bin"
    with open(filename, "wb") as f:   # wb = 二进制写入
        f.write(data)
    print(f"Saved {len(data)} bytes → {filename}")
    # print(f"type: {type(data.decode())}")
    # information.append(json.loads(data.decode()))

with open("information.ndjson", "w") as f:
    for item in information:
        f.write(json.dumps(item) + "\n")
