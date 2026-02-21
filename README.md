# Picamera

基于树莓派和普通 Web 摄像头的 Python 图传监控系统。

## 系统架构

![系统说明](file/picamera01.png)

系统由三个部分组成：

| 组件 | 文件 | 运行位置 | 说明 |
|------|------|----------|------|
| Socket 客户端 | `socket_client.py` | 树莓派 | 通过 USB 摄像头采集图像，经 Socket 发送至服务器 |
| TCP 服务器 | `server.py` | Linux 服务器 | 接收图像数据，保存到磁盘并缓存至内存 |
| HTTP 服务器 | `server.py`（内嵌） | Linux 服务器 | 响应浏览器的 HTTP GET 请求，返回最新图像 |

## 通信协议

客户端与服务器之间使用自定义二进制协议，通过 TCP 端口 **10086** 通信。

### 图片上传协议

```
┌──────────────────── 头部（struct 'IdI'）────────────────────┐
│  设备 ID (4B, int)  │  时间戳 (8B, double)  │  文件大小 (4B, uint)  │
└─────────────────────────────────────────────────────────────┘
│                        JPEG 数据流                           │
│                 （每次发送 1024 字节分块）                      │
└─────────────────────────────────────────────────────────────┘
```

- 服务器收到后保存至 `upload/d_{设备ID}.jpg`，同时缓存到内存供 HTTP 请求使用
- 服务器通过时间戳判断是否为最新图片，拒绝过时数据
- 每设备有独立写锁（`threading.Lock`），防止并发写入冲突

### 图片请求协议

当服务器检测到请求头部以 `GET` 开头时，判定为 HTTP 图片请求，返回标准 HTTP 响应（含 `Content-Type: image/jpeg` 等响应头）和内存中缓存的最新图片。若无可用图片，返回 HTTP 404。

## 快速开始

### 环境要求

- Python 3.6+
- 仅使用标准库（`socketserver`、`socket`、`struct`、`os`、`time`、`threading`、`logging`、`argparse`）

### 启动服务器

```bash
# 默认监听 0.0.0.0:10086
python server.py

# 自定义地址和端口
python server.py --host 192.168.1.100 --port 8080
```

### 发送测试图片

```bash
# 发送指定图片
python socket_client.py upload/bbb.jpg

# 自定义服务器地址、端口和设备 ID
python socket_client.py photo.jpg --host 192.168.1.100 --port 8080 --device-id 2
```

### 浏览器查看

打开 `test_html.html`（内置每 2 秒自动刷新），或直接访问：

```
http://127.0.0.1:10086/latest.jpg
```

### 命令行帮助

```bash
python server.py --help
python socket_client.py --help
```

## 项目结构

```
Picamera/
├── server.py           # TCP/HTTP 服务器
├── socket_client.py    # Socket 客户端
├── test_html.html      # 浏览器监控测试页面（自动刷新）
├── upload/             # 接收到的图片存储目录
└── file/
    └── picamera01.png  # 系统架构图
```

## 待改进

- **图像跟踪与识别**：规划中的 OpenCV 功能尚未实现

## 联系方式

- 文档：https://loadstarcn.github.io/Picamera/
- 邮箱：richard@olive-app.com
