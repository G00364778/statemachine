import select, socket, sys, queue
from time import sleep
import json
import os.path as ospath
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)
server.bind(('localhost', 50000))
server.listen(5)
inputs = [server]
outputs = []
message_queues = {}
timeout = 1 # the timout value in seconds, "None" to disable
MachineState = 'unknown'
PVList={}

def PVSet (name,val):
    PVList[name]=val
    PVStr=json.dumps(PVList)
    return PVStr

def SavePVList():
    with open('pv.dump', 'w') as outfile:
        json.dump(PVList,outfile)


def StateMachineProcess(Message):
    global MachineState
    global PVList
    Message=Message.lower()
    #states=['unknown', 'init', 'init-done', 'job-start', 'recipe-start', 'recipe-end', 'job-end', 'exception']
    #print('Command: {1} State: {0}'.format(MachineState, Message))
    #if Message in states:
    if Message == '?':
        pass
    elif (MachineState == 'unknown' or MachineState == 'complete' or MachineState == 'abort') \
     and Message == 'init':
        if ospath.isfile('pv.dump'):
            with open('pv.dump') as jsondmp:
                PVList=json.load(jsondmp)
        MachineState = 'init'
    elif MachineState == 'init' and Message == 'select':
        MachineState='select'
    elif MachineState == 'select' and Message == 'run':
        MachineState ='run'
    elif MachineState == 'run' and Message == 'exception':
        MachineState ='exception'
    elif MachineState == 'exception' and Message == 'warn':
        MachineState='warn'
    elif MachineState == 'exception' and Message == 'alarm':
        MachineState='alarm'
    elif (MachineState == 'warning' or MachineState == 'exception' or MachineState == 'alarm' \
     or MachineState == 'run' or MachineState == 'select') and Message == 'abort':
        MachineState ='abort'
    elif (MachineState == 'abort' or MachineState == 'init') and Message == 'kill':
        MachineState = 'kill'
    elif (MachineState == 'run' or MachineState == 'warn') and Message == 'complete':
        MachineState ='complete'
    else: 
        #check for variable commands valset or valread
        if Message.lower().startswith('valset'): 
            name,sep,val=Message.replace('valset ','').partition('=')
            PVStr=PVSet(name,val)
            print('PVList: ',PVStr)
            return PVStr
        elif Message.lower().startswith('valget'): 
            PVStr=json.dumps(PVList)
            return PVStr
        elif Message.lower().startswith('valrm'): 
            Message=Message.replace('valrm ','')
            print('\t\tvalrm: "{}"'.format(Message))
            
            del PVList[Message]
            PVStr=json.dumps(PVList)
            return PVStr
        else:
            return 'command unknow or out of sequence....'
    #print('  SetState...',MachineState)
    PVList['MachineState']=MachineState
    if MachineState != 'unknown':
        SavePVList()
    return MachineState


while inputs:
    if MachineState != 'kill':
        counter=0
    if MachineState == 'kill':
        counter+=1
    if MachineState == 'kill' and counter >= 10:
        if s in outputs:
            outputs.remove(s)
        inputs.remove(s)
        s.close()
        del message_queues[s]
        with open('pv.dump', 'w') as outfile:
            json.dump(PVList,outfile)
        print('\t\t\tState: {} ... terminating server....'.format(MachineState))
        exit()

    #check the socket for write, read or exceptions - waiting here unles timout is set
    #readable, writable, exceptional = select.select(inputs, outputs, inputs)
    readable, writable, exceptional = select.select(inputs, outputs, inputs,timeout)
    for s in readable:
        #print('incoming message ...')
        if s is server: # if a client connection arrived
            connection, client_address = s.accept() #accept connection
            connection.setblocking(0)
            inputs.append(connection) # add a return socket for inputs
            message_queues[connection] = queue.Queue() # adds a queue for incoming message
            print('\tconnect..',client_address)
        else:
            #print('\tread message')
            data = s.recv(1024) # do a non blocking read if there is data
            if data:
                msg='{}'.format(data.decode())
                #print('\t\tdata received: {}'.format(msg))
                status=StateMachineProcess(msg)
                message_queues[s].put(status.encode())
                #if data.decode() == 'quit':
                #    message_queues[s].put(b'ack-quit')
                #elif data.decode() == 'init':
                #    message_queues[s].put(b'ack-init')
                #else:
                #    message_queues[s].put(data)
                if s not in outputs:
                    outputs.append(s)
            else:
                print('\t\tclient disconnected')
                if s in outputs:
                    outputs.remove(s)
                inputs.remove(s)
                s.close()
                del message_queues[s]
                if MachineState == 'killed':
                    SavePVList()
                    #with open('pv.dump', 'w') as outfile:
                    #    json.dump(PVList,outfile)
                    print('\t\t\tState: {} ... terminating server....'.format(MachineState))
                    exit()

    for s in writable:
        #print('outgoing message...')
        try:
            #print('\ttry to queue message..')
            next_msg = message_queues[s].get_nowait()
        except queue.Empty:
            #print('\tqueue empty, remove..')
            outputs.remove(s)
        else:
            #print('\tsending..')
            s.send(next_msg)

    for s in exceptional:
        print('exception occured...')
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
        del message_queues[s]
