#-*-coding:utf-8-*-

import socket 
import os
import sys
import struct

# data of socket and file datapath 
ADDR = ('127.0.0.1',10086)
BUFSIZE = 1024
filename = 'bbb.jpg'
FILEINFO_SIZE=struct.calcsize('128s32sI8s')

# 客户端发送文件
def Send_File_Client():
    sendSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sendSock.connect(ADDR)

    fhead=struct.pack('128s11I',filename,0,0,0,0,0,0,0,0,os.stat(filename).st_size,0,0)

    sendSock.send(fhead)
    fp = open(filename,'rb')

    while 1:
        filedata = fp.read(BUFSIZE)
        if not filedata: 
            break
        sendSock.send(filedata)
    print u"文件传送完毕，正在断开连接...\n"

    fp.close()
    sendSock.close()
    print u"连接已关闭...\n" 

if __name__ == '__main__':
    Send_File_Client()