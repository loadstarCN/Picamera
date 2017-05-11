#-*-coding:utf-8-*-
#创建SocketServerTCP服务器：  
import SocketServer  
from SocketServer import StreamRequestHandler as SRH  
from time import ctime  
import struct,os

host = '0.0.0.0'  
port = 10086  
addr = (host,port) 

FILEINFO_SIZE=struct.calcsize('IdI') 
BUFSIZE= 1024

device_pic_time_dict={}
device_pic_write_dict={}

UPLOAD_FOLDER="upload"
if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

class Servers(SRH):  
    def handle(self):  
        print u"客户端已连接—> \n",self.client_address
        fhead = self.request.recv(FILEINFO_SIZE)
        d_id,pic_time,filesize=struct.unpack('IdI',fhead)
        print(u"[头部信息] ID:{} 时间:{} 文件长度:{} \n".format(d_id,pic_time,filesize))

        #todo根据time信息判断是否为最新图片
        last_time=device_pic_time_dict.get(d_id)
        
        if not last_time or last_time<pic_time:
            device_pic_time_dict[d_id]=pic_time
        
            is_write=device_pic_write_dict.get(d_id)

            if not is_write:
                device_pic_write_dict[d_id]=True
              
                
                filename=os.path.join(UPLOAD_FOLDER,'d_{}.jpg'.format(str(d_id)))

                fp = open(filename,'wb')
                restsize = filesize
                print(u"开始接收文件... \n")
                
                while True:
                    try:  
                        data = self.request.recv(1024)  
                        if not data:   
                            break  
                        
                        #print("接收文件长度:{} \n".format(len(data)))
                        fp.write(data)

                    except Exception as ex:  
                        print ex.message
                        break

                print(u"接收文件完毕,正在断开连接... \n")
                fp.close() 
                device_pic_write_dict[d_id]=False
            else:
                print(u"文件正在读写,终止操作 \n")
        else:
            print(u"文件s数据过时,终止操作 \n")
        print(device_pic_time_dict)
        print(device_pic_write_dict)




print '服务器开始运行....'  
server = SocketServer.ThreadingTCPServer(addr,Servers)  
server.serve_forever()  