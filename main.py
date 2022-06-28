####################################
#
# Atividade 1 Sockets Python
# 
# Andre L G Santos 2090279
#
####################################


import select
import socket
import errno
import sys
import uuid
from datetime import datetime
from threading import Thread
import time
import pickle


REQUEST = 1
REPLY = 2
SENT = 3
EXEC = 4

IP = socket.gethostbyname(socket.gethostname())
PORT = 5050
ProcID = str(uuid.uuid1())[:8]
ProcTime = f"{int(round((datetime.now()).timestamp()))}"

HEADER_LENGTH = 10
CS_TIME = 5
RepList = []
ReqList = []
ReqList_count = 0

Executing = False
Executed = False
Requested = False
RequestedTime = 0

ServerOn = False
ClientOn = False

Server_Socket = {}
Client_Socket = {}
Clients = {}

def logicalClock():
    now = datetime.now()
    seconds_day = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    logicalClock = int(seconds_day)
    return logicalClock


def executeCS():
    try : 
        global Requested
        global Executing
        Executing = True
        Requested = False
        ReqList.clear()
        print (f"Processo : {ProcID} : Rodando secao critica em: {logicalClock()}")
        time.sleep(CS_TIME)
        print (f"Processo : {ProcID} : Rodando secao critica em: {logicalClock()}")
        Executing = False
        return True
    except Exception as e :
        return False


def receive_message_client():

    try:
        # Receive our "header" containing message length, it's size is defined and constant
        message_header = Client_Socket.recv(HEADER_LENGTH)

        if len(message_header) == 0:
            return False

        message_length = int(message_header.decode('utf-8').strip())
        data = pickle.loads(Client_Socket.recv(message_length))
        # Return an object of message header and message data
        return data

    except:
        return False


def receive_message_server(Client_Socket):

    try:
        message_header = Client_Socket.recv(HEADER_LENGTH)
        if len(message_header) == 0:
            return False

        message_length = int(message_header.decode('utf-8').strip())
        data = pickle.loads(Client_Socket.recv(message_length))
        return data

    except:
        return False


def localServer():

    try:
        Server_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        Server_Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        Server_Socket.bind((IP, PORT))
        Server_Socket.listen()
        sockets_list = [Server_Socket]
    except:
        return

    while True:
        sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        for subscriber in sockets:

            if subscriber == Server_Socket:

                Client_Socket, client_address = Server_Socket.accept()
                message = receive_message_server(Client_Socket)
                if message is False:
                    continue

                sockets_list.append(Client_Socket)
                Clients[Client_Socket] = message

                # print('Accepted new connection from {}:{}, Process ID: {}'.format(*client_address, message['ProcID']))

            else:

                # Receive message
                message = receive_message_server(subscriber)

                if message is False:
                    # print('Closed connection from: {}'.format(Clients[subscriber]['ProcID']))

                    # Remove from list for socket.socket()
                    sockets_list.remove(subscriber)

                    # Remove from our list of users
                    del Clients[subscriber]

                    continue

                processInfo = Clients[subscriber]

                # print(f'Received message from {processInfo["ProcID"]}: {message}')

                if int(message["qualMsg"]) == REQUEST:
                    count = 0
                    # print(f"Broadcasting Request message from {message['veioDe']}")
                    for Client_Socket in Clients:
                        if Client_Socket != subscriber:
                            msg_header = f"{len(pickle.dumps(message)):<{HEADER_LENGTH}}".encode('utf-8')
                            Client_Socket.send(msg_header + pickle.dumps(message))
                            count += 1
                    count_message={'qualMsg': SENT, 'contaEnvio': count}
                    count_msg_header = f"{len(pickle.dumps(count_message)):<{HEADER_LENGTH}}".encode('utf-8')
                    subscriber.send(count_msg_header + pickle.dumps(count_message))

                if int(message["qualMsg"]) == EXEC:
                    # print(f"Broadcasting Executing message from {message['veioDe']}")
                    for Client_Socket in Clients:
                        if Client_Socket != subscriber:
                            msg_header = f"{len(pickle.dumps(message)):<{HEADER_LENGTH}}".encode('utf-8')
                            Client_Socket.send(msg_header + pickle.dumps(message))

                if int(message["qualMsg"]) == REPLY:
                    # print(f"Sending REPLY message to {message['foiPara']}")
                    for Client_Socket in Clients:
                        info = Clients[Client_Socket]
                        if info["ProcID"] == message["foiPara"]:
                            rep_msq_header = f"{len(pickle.dumps(message)):<{HEADER_LENGTH}}".encode('utf-8')
                            Client_Socket.send(rep_msq_header + pickle.dumps(message))

        for subscriber in exception_sockets:

            # Remove from list for socket.socket()
            sockets_list.remove(subscriber)

            # Remove from our list of users
            del Clients[subscriber]

while True:
    
    if ServerOn == False:
        Thread(target=localServer).start()
        ServerOn = True

    if ClientOn == False:
        Client_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        Client_Socket.connect((IP, PORT))
        Client_Socket.setblocking(False)
        intro={'ProcID': ProcID,'procTemp': ProcTime}
        intro_header = f"{len(pickle.dumps(intro)):<{HEADER_LENGTH}}".encode('utf-8')
        Client_Socket.send(intro_header + pickle.dumps(intro))
        ClientOn = True
    
    option = input(f'Digite 1 entrar na secao critica, Enter para atualizar: ')
    if option and int(option.strip()) == REQUEST and not Requested:
        print (f"Pedindo acesso no tempo: {str(logicalClock())}")
        msg = {
            'veioDe': ProcID,
            'qualMsg': REQUEST,
            'horario': logicalClock(), 
            'procTemp': ProcTime
            }
        RequestedTime = msg['horario']
        Requested = True
        msg_header = f"{len(pickle.dumps(msg)):<{HEADER_LENGTH}}".encode('utf-8')
        Client_Socket.send(msg_header + pickle.dumps(msg))

    try:
        while True:
            if Executed:
                print(f"Enviando para os proximos da secao critica")
                for rep in RepList:
                    print(f"Envio : {ProcID} --> {rep['veioDe']}")
                    RepList_msq= {'qualMsg': REPLY, 'foiPara': rep['veioDe']}
                    RepList_msq_header = f"{len(pickle.dumps(RepList_msq)):<{HEADER_LENGTH}}".encode('utf-8')
                    Client_Socket.send(RepList_msq_header + pickle.dumps(RepList_msq))
                RepList.clear()
                Executed = False
            servmsg = receive_message_client()

            if servmsg is False:
                print('Não recebeu nada ainda')
                raise RuntimeError()

            if int(servmsg['qualMsg']) == REQUEST:
                if Executing:
                    for rep in RepList:
                        if rep['veioDe'] == servmsg['veioDe']:
                            print (f"Pedido de {rep['veioDe']} já na lista")
                            raise RuntimeError()
                    RepList.append(servmsg)
                    print(f"Adicionando na lista o processo ({ProcID}) e exucutando a secao critica")
                else:
                    if Requested and (ProcTime < servmsg['procTemp'] or servmsg['horario'] > RequestedTime):
                        RepList.append(servmsg)
                        print(f"Adicionando a lista {servmsg['veioDe']} ja que o processo ({ProcID}) tem maior prioridade")
                    else:
                        print(f"Enviando resposta para {servmsg['veioDe']} para sua requisicao em: {servmsg['horario']}")
                        rep_msq= {'qualMsg': REPLY, 'foiPara': servmsg['veioDe']}
                        rep_msq_header = f"{len(pickle.dumps(rep_msq)):<{HEADER_LENGTH}}".encode('utf-8')
                        Client_Socket.send(rep_msq_header + pickle.dumps(rep_msq))
            
            if int(servmsg['qualMsg']) == SENT:
                print(f"Pedido enviado para: {servmsg['contaEnvio']}; de: {ProcID}")
                ReqList_count=servmsg['contaEnvio']
            
            if int(servmsg['qualMsg']) == REPLY:
                print(f"Resposta recebida no: {ProcID}")
                ReqList.append(servmsg)
                if ReqList_count == len(ReqList):
                    print("Respostas recebidas dos processos: "+str(ReqList_count)+"")
                    ReqList_count -= len(ReqList)
                    if (ReqList_count == 0):
                        msg_exec= {'qualMsg': EXEC, 'veioDe': ProcID, 'horario': logicalClock()}
                        msg_header = f"{len(pickle.dumps(msg_exec)):<{HEADER_LENGTH}}".encode('utf-8')
                        Client_Socket.send(msg_header + pickle.dumps(msg_exec))
                        ecs = executeCS()
                        if ecs and len(RepList) > 0:
                            Executed = True
                            
            if int(servmsg['qualMsg']) == EXEC:
                print(f"{servmsg['veioDe']} esta utilizando a secao critica no tempo: {servmsg['horario']}")

    except IOError as e:
        if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
            print('\nReading error: {}'.format(str(e)))
            sys.exit()

        # We just did not receive anything
        continue
    except RuntimeError as e:
        continue

    except Exception as e:
        # Any other exception - something happened, exit
        print('\nReading error: '.format(str(e)))
        sys.exit()