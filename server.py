"""Picamera TCP/HTTP 图传服务器

同时处理两种请求：
- 二进制协议：接收客户端上传的 JPEG 图片（16 字节头部 + 数据流）
- HTTP GET：返回内存中缓存的最新图片
"""

import socketserver
from socketserver import StreamRequestHandler
import struct
import os
import logging
import argparse
import threading
from typing import Dict, Optional

# ── 常量 ──────────────────────────────────────────────

HEADER_SIZE = struct.calcsize('IdI')  # 设备ID(4B) + 时间戳(8B) + 文件大小(4B)
BUFSIZE = 1024
UPLOAD_FOLDER = "upload"

# ── 日志 ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 线程安全的设备状态管理 ─────────────────────────────


class DeviceState:
    """管理设备图片数据，所有操作均线程安全。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pic_times: Dict[int, float] = {}
        self._writing: Dict[int, bool] = {}
        self._pic_data: Optional[bytes] = None

    def get_pic_data(self) -> Optional[bytes]:
        """获取最新的图片数据。"""
        with self._lock:
            return self._pic_data

    def try_begin_write(self, device_id: int, pic_time: float) -> bool:
        """尝试开始写入，返回 True 表示允许写入。

        拒绝写入的情况：图片时间戳过旧，或该设备正在写入中。
        """
        with self._lock:
            last_time = self._pic_times.get(device_id)
            if last_time is not None and last_time >= pic_time:
                return False
            if self._writing.get(device_id, False):
                return False
            self._pic_times[device_id] = pic_time
            self._writing[device_id] = True
            return True

    def finish_write(self, device_id: int, data: Optional[bytes]) -> None:
        """完成写入，更新图片缓存并释放写锁。"""
        with self._lock:
            if data is not None:
                self._pic_data = data
            self._writing[device_id] = False


state = DeviceState()

# ── 请求处理器 ────────────────────────────────────────


class ImageRequestHandler(StreamRequestHandler):
    """处理图片上传（二进制协议）和图片请求（HTTP GET）。"""

    def handle(self) -> None:
        client = f"{self.client_address[0]}:{self.client_address[1]}"
        logger.info(f"客户端已连接: {client}")

        fhead = self.request.recv(HEADER_SIZE)
        if not fhead:
            return

        if fhead[:3] == b'GET':
            self._handle_http(fhead)
        else:
            self._handle_upload(fhead)

    def _handle_http(self, initial_data: bytes) -> None:
        """处理 HTTP GET 请求，返回最新图片。"""
        # 读取剩余的 HTTP 请求头
        self.request.recv(4096)
        logger.info("收到 HTTP 图片请求")

        pic_data = state.get_pic_data()
        if pic_data:
            header = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(pic_data)).encode() + b"\r\n"
                b"Connection: close\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"\r\n"
            )
            self.request.sendall(header + pic_data)
        else:
            body = b"No image available"
            header = (
                b"HTTP/1.1 404 Not Found\r\n"
                b"Content-Type: text/plain; charset=utf-8\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )
            self.request.sendall(header + body)

    def _handle_upload(self, fhead: bytes) -> None:
        """处理二进制协议图片上传。"""
        if len(fhead) < HEADER_SIZE:
            logger.warning(f"头部数据不完整: 收到 {len(fhead)} 字节，需要 {HEADER_SIZE} 字节")
            return

        device_id, pic_time, filesize = struct.unpack('IdI', fhead)
        logger.info(f"[头部信息] 设备ID: {device_id}  时间戳: {pic_time}  文件大小: {filesize}")

        if not state.try_begin_write(device_id, pic_time):
            logger.info(f"设备 {device_id}: 写入被拒绝（数据过时或正在写入中）")
            return

        try:
            filename = os.path.join(UPLOAD_FOLDER, f"d_{device_id}.jpg")
            chunks: list = []
            received = 0

            with open(filename, 'wb') as fp:
                logger.info("开始接收文件...")
                while True:
                    data = self.request.recv(BUFSIZE)
                    if not data:
                        break
                    fp.write(data)
                    chunks.append(data)
                    received += len(data)

            pic_bytes = b"".join(chunks)
            state.finish_write(device_id, pic_bytes)
            logger.info(f"文件接收完毕: {received} 字节 -> {filename}")

        except Exception:
            logger.exception(f"接收设备 {device_id} 的文件时出错")
            state.finish_write(device_id, None)


# ── 主入口 ────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Picamera 图传服务器")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址（默认: 0.0.0.0）")
    parser.add_argument("--port", type=int, default=10086, help="绑定端口（默认: 10086）")
    args = parser.parse_args()

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    server = socketserver.ThreadingTCPServer((args.host, args.port), ImageRequestHandler)
    server.daemon_threads = True

    logger.info(f"服务器启动，监听 {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("正在关闭服务器...")
        server.shutdown()


if __name__ == "__main__":
    main()
