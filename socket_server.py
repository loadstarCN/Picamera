#-*-coding:utf-8-*-

import socket 
import struct

# data of socket and file datapath 
ADDR = ('0.0.0.0',10086)
BUFSIZE = 1024
FILEINFO_SIZE=struct.calcsize('128s32sI8s')

# 接受文件的服务器端
def Reveiver_File_Server():

    recvSock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    recvSock.bind(ADDR)
    recvSock.listen(20)
    print u"等待连接...\n"

    conn,addr = recvSock.accept()
    print u"客户端已连接—> \n",addr

    fhead = conn.recv(FILEINFO_SIZE)
    filename,temp1,filesize,temp2=struct.unpack('128s32sI8s',fhead)
    print filename,temp1,filesize,temp2
    print filename,len(filename),type(filename)
    print filesize

    filename = 'new_'+filename.strip('\00') #...
    fp = open(filename,'wb')
    restsize = filesize
    print u"正在接收文件... \n",

    while True:
        if restsize > BUFSIZE:
            filedata = conn.recv(BUFSIZE)
        else:
            filedata = conn.recv(restsize)
        if not filedata: 
            break
        fp.write(filedata)
        restsize = restsize-len(filedata)
        if restsize == 0:
            break
    print u"接收文件完毕，正在断开连接...\n"
    fp.close()
    conn.close()
    recvSock.close()
    print u"连接已关闭...\n"

if __name__ == '__main__':
    Reveiver_File_Server()