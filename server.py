import socket
state='unknown'
 
def Main():
    host = "127.0.0.1"
    port = 5000
    
    mySocket = socket.socket()
    mySocket.bind((host,port))
    mySocket.listen(1)
    mySocket.settimeout(5)
        
    conn, addr = mySocket.accept() #server waits for a connection here
    print ("Connection from: " + str(addr))
    while True: # loops forever untill break
        
        data = conn.recv(1024).decode()
        if not data: # when client disconnect I go here
            break
        print ("received: " + str(data))
        conn.send('ack'.encode())
        print('data: "{}"'.format(data))
         
    conn.close() # on break, close connection
     
if __name__ == '__main__':
    Main()
