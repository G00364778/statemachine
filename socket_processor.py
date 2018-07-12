import socket
from time import sleep
 
def sock_proc_states():
    host = '127.0.0.1'
    port = 50000
        
    mySocket = socket.socket()
    mySocket.connect((host,port))
    active=True
    state=''
        
    while active:
        sleep(1)
        mySocket.send('?'.encode())
        data = mySocket.recv(1024).decode()
        if data != state:
            print ('Received from server: ' + data)
        if data == 'killed':
            active = False
        state=data

    print('Terminating socket client...')
    mySocket.close() # close on quit
 
if __name__ == '__main__':
    sock_proc_states()