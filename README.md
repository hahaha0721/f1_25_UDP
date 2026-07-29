# F1 25 UDP Telemetry

解析 F1 25 游戏的 UDP 遥测数据。包含完整的二进制协议解码器，支持全部 14 种数据包类型。

## 项目结构

```
f125/
├── batch_parse.py          # 批量解析二进制 UDP 包 → NDJSON
├── udp_receiver.py         # 实时接收 UDP 包并保存为 .bin
└── packets/
    └── samples/            # 每种包类型的二进制样本（官方协议）
```

## 快速开始

### 解析已捕获的数据包

```bash
python3 batch_parse.py
# 输出: parsed_packets.ndjson（每行一个 JSON 对象）
```

### 实时捕获 UDP 数据

```bash
python3 udp_receiver.py
# 监听 0.0.0.0:20777，每个包保存为 packets/<timestamp>_<port>.bin
```

## 数据包类型

| ID | 名称 | 大小 | 说明 |
|----|------|------|------|
| 0 | Motion | 1349 | 22 辆车的位置/速度/G力 |
| 1 | Session | 753 | 赛道/天气/旗语/设置 |
| 2 | Lap Data | 1285 | 圈速/分段/位置 |
| 3 | Event | 45 | 按钮/DRS/碰撞等事件 |
| 4 | Participants | 1284 | 车手/车队信息 |
| 5 | Car Setups | 1133 | 翼片/悬挂/胎压/油量 |
| 6 | Car Telemetry | 1352 | 速度/油门/刹车/胎温 |
| 7 | Car Status | 1239 | 燃油/ERS/DRS 状态 |
| 10 | Car Damage | 1041 | 轮胎磨损/车辆损伤 |
| 11 | Session History | 1460 | 历史圈速/轮胎记录 |
| 12 | Tyre Sets | 231 | 可用轮胎组 |
| 13 | Motion Ex | 273 | 悬挂/轮胎物理扩展数据 |
| 14 | Time Trial | 101 | 计时赛对比数据 |
| 15 | Lap Positions | 1131 | 每圈排位 |

## 协议说明

游戏通过 UDP 端口 20777 发送二进制数据包。每个包的前 29 字节是公共头：

- `uint16` packet_format (2025)
- `uint8[4]` 版本信息
- `uint8` packet_id
- `uint64` session_uid
- `float` session_time
- `uint32[2]` frame_identifier
- `uint8[2]` player_car_index

## 文件格式

- `.bin` — 原始二进制 UDP 包
- `.ndjson` — Newline Delimited JSON，每行一个完整的 JSON 对象
