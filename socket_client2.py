from socket import *  
  
host = '127.0.0.1'  
port = 9999  
bufsize = 1024  
addr = (host,port)  
client = socket(AF_INET,SOCK_STREAM)  
client.connect(addr)  
while True:  
    data = raw_input()  
    if not data or data=='exit':  
        break  
    client.send('%s\r\n' % data)  
    data = client.recv(bufsize)  
    if not data:  
        break  
    print data.strip()  
client.close()  