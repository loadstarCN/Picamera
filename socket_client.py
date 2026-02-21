"""Picamera Socket 客户端

将本地 JPEG 图片通过二进制协议发送到 Picamera 服务器。
协议格式：16 字节头部 (设备ID + 时间戳 + 文件大小) + JPEG 数据流
"""

import socket
import os
import struct
import time
import logging
import argparse

BUFSIZE = 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def send_file(host: str, port: int, device_id: int, filepath: str) -> None:
    """将指定图片文件发送到服务器。"""
    filesize = os.path.getsize(filepath)
    header = struct.pack('IdI', device_id, time.time(), filesize)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        logger.info(f"已连接到 {host}:{port}")

        sock.sendall(header)

        with open(filepath, 'rb') as fp:
            while True:
                chunk = fp.read(BUFSIZE)
                if not chunk:
                    break
                sock.sendall(chunk)

    logger.info(f"文件发送完毕: {filepath} ({filesize} 字节)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Picamera 图片发送客户端")
    parser.add_argument("file", help="要发送的 JPEG 文件路径")
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址（默认: 127.0.0.1）")
    parser.add_argument("--port", type=int, default=10086, help="服务器端口（默认: 10086）")
    parser.add_argument("--device-id", type=int, default=1, help="设备 ID（默认: 1）")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        logger.error(f"文件不存在: {args.file}")
        return

    send_file(args.host, args.port, args.device_id, args.file)


if __name__ == "__main__":
    main()
