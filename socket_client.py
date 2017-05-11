#-*-coding:utf-8-*-

import socket 
import os
import sys
import struct
import time

# data of socket and file datapath 
ADDR = ('127.0.0.1',10086)
BUFSIZE = 1024
filename = 'upload/bbb.jpg'


# 客户端发送文件
def Send_File_Client():
    sendSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sendSock.connect(ADDR)

    fhead=struct.pack('IdI',1,float(time.time()),os.stat(filename).st_size)
    print(fhead)
    sendSock.send(fhead)
    fp = open(filename,'rb')

    while 1:
        filedata = fp.read(BUFSIZE)
        if not filedata: 
            break
        sendSock.send(filedata)
    
    '''
    print u"文件传送完毕，正在断开连接...\n"

    fp.close()
    sendSock.close()
    print u"连接已关闭...\n" 

    '''

if __name__ == '__main__':
    Send_File_Client()