####################################
#
# Atividade 1 Sockets Python
# 
# Andre L G Santos 2090279
#
####################################


import select
import socket
from threading import Thread
import sys # Para apenas caso precise sair do programa
import pickle # Pra codificar via socket
import errno # Apenas para Erro de conexao
import uuid # Pra gerar um ID unico
import time # Ambos datetime e time usados no relogio logico
from datetime import datetime

# Tipo de mensagem a ser lido por cada socket
REQUEST = 1
REPLY = 2
SENT = 3
EXEC = 4

# Credenciais de cada processo
IP = socket.gethostbyname(socket.gethostname())
PORT = 5050
ProcID = str(uuid.uuid1())[:8] # Respqctivamente 'Pi' do algoritmo de Agrawala
ProcTime = f"{int(round((datetime.now()).timestamp()))}" # Respectivamente 'Ti'do algoritmo de Agrawala

# Variaveis de adequacao para envio de mensagem, tempo de uso da SC e Lista de Espera
HEADER_LENGTH = 10
CS_TIME = 5
RepList = []
ReqList = []
ReqList_count = 0

# Variaveis de estado e tempo
Executing = False
Executed = False
Requested = False
RequestedTime = 0

# Variaveis para validacao de conexao
ServerOn = False
ClientOn = False

# Variaveis para incremento de novos processos
Server_Socket = {}
Client_Socket = {}
Clients = {}

# Funcao que retorna a quantidade de segundo passado apos 0h (Relogio Logico)
def logicalClock():
    now = datetime.now()
    seconds_day = (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    logicalClock = int(seconds_day)
    return logicalClock

# Funcao que executa o processo na secao critica e settando o estado
def executeCS():
    try : 
        global Requested
        global Executing
        Executing = True
        Requested = False
        ReqList.clear()
        print (f"{ProcID} -> Processo : {ProcID} : Iniciando secao critica em: {logicalClock()}")
        time.sleep(CS_TIME)
        print (f"{ProcID} -> Processo : {ProcID} : Finalizado secao critica em: {logicalClock()}")
        Executing = False
        return True
    except Exception as e :
        return False

# Funcao que recebe a mensagem vinda do cliente
def receive_message_client():

    try:
        # Recebe a mensagem contendo tamanho, comprimento e as constantes
        message_header = Client_Socket.recv(HEADER_LENGTH)

        # Se vier vazia ja retorna falso
        if len(message_header) == 0:
            return False

        message_length = int(message_header.decode('utf-8').strip())
        data = pickle.loads(Client_Socket.recv(message_length))
        # Retorna um objeto contendo os dados da msg
        return data

    except:
        return False

# Funcao que recebe a mensagem vinda dde cada cliente, contendo quem requisitou
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

# Essa funcao inicia, via thread, uma unica instancia que fica escutando o socket do cliente,
# atualizando a fila de requisicoes e prioridades
def localServer():

    Server_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Server_Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        Server_Socket.bind((IP, PORT))
        Server_Socket.listen()
    except:
        return
    
    sockets_list = [Server_Socket]

    while True:
        sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

        for subscriber in sockets:

            # Essa funcao e referente ao multi-cast (Que nao esta implementado ainda)
            if subscriber == Server_Socket:

                Client_Socket, client_address = Server_Socket.accept()
                message = receive_message_server(Client_Socket)
                if message is False:
                    continue

                sockets_list.append(Client_Socket)
                Clients[Client_Socket] = message

                # print('Accepted new connection from {}:{}, Process ID: {}'.format(*client_address, message['ProcID']))

            else:

                # Recebe a mensagem contendo os dados do cliente
                message = receive_message_server(subscriber)

                # Se nao recebeu nada, remove o sockets e da lista de clientes
                if message is False:
                    sockets_list.remove(subscriber)
                    del Clients[subscriber]
                    continue

                processInfo = Clients[subscriber]

                # print(f'\n\n{ProcID} -> Mensagem recebida de: {processInfo["ProcID"]}: {message}\n')

                # Se a mensagem for do tipo de requisicao, executa fila de requisicoes
                if int(message["qualMsg"]) == REQUEST:
                    
                    count = 0
                    for Client_Socket in Clients:
                        if Client_Socket != subscriber:
                            msg_header = f"{len(pickle.dumps(message)):<{HEADER_LENGTH}}".encode('utf-8')
                            Client_Socket.send(msg_header + pickle.dumps(message))
                            count += 1
                    count_message={
                        'qualMsg': SENT, 
                        'contaEnvio': count
                        }
                    count_msg_header = f"{len(pickle.dumps(count_message)):<{HEADER_LENGTH}}".encode('utf-8')
                    subscriber.send(count_msg_header + pickle.dumps(count_message))

                # Se a mensagem for do tipo de resposta, executa fila de respostas
                if int(message["qualMsg"]) == EXEC:
                    # print(f"Broadcasting Executing message from {message['veioDe']}")
                    for Client_Socket in Clients:
                        if Client_Socket != subscriber:
                            msg_header = f"{len(pickle.dumps(message)):<{HEADER_LENGTH}}".encode('utf-8')
                            Client_Socket.send(msg_header + pickle.dumps(message))

                # Se a mensagem for do tipo de resposta, executa fila de respostas
                if int(message["qualMsg"]) == REPLY:
                    # print(f"Sending REPLY message to {message['foiPara']}")
                    for Client_Socket in Clients:
                        info = Clients[Client_Socket]
                        if info["ProcID"] == message["foiPara"]:
                            rep_msq_header = f"{len(pickle.dumps(message)):<{HEADER_LENGTH}}".encode('utf-8')
                            Client_Socket.send(rep_msq_header + pickle.dumps(message))

        for subscriber in exception_sockets:
            sockets_list.remove(subscriber)
            del Clients[subscriber]

# Funcao principal que inicia o programa
while True:
    
    # Checa se o localserver já está ligado, para receber novos processos
    if ServerOn == False:
        Thread(target=localServer).start()
        ServerOn = True

    # Evita que o cliente refaca a conexao a cada loop
    if ClientOn == False:
        # Envia ao localserver o PID do processo
        Client_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        Client_Socket.connect((IP, PORT))
        Client_Socket.setblocking(False)
        intro={
            'ProcID': ProcID,
            'procTemp': ProcTime
            }
        intro_header = f"{len(pickle.dumps(intro)):<{HEADER_LENGTH}}".encode('utf-8')
        Client_Socket.send(intro_header + pickle.dumps(intro))
        ClientOn = True
    
    option = input(f'{ProcID} -> Digite 1 entrar na secao critica, Enter para atualizar: ')
    if option and int(option.strip()) == REQUEST and not Requested:
        print (f"{ProcID} -> Pedindo de acesso no tempo: {str(logicalClock())}")
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
            # Se foi executado passa e avisa o proximo processo
            if Executed:
                print(f"{ProcID} -> Enviando para os proximos da secao critica")
                # Printa cada um dos processos que estao aguardando na 'fila'
                for rep in RepList:
                    print(f"{ProcID} -> Envio : {ProcID} -> {rep['veioDe']}")
                    RepList_msq= {
                        'qualMsg': REPLY, 
                        'foiPara': rep['veioDe']
                        }
                    RepList_msq_header = f"{len(pickle.dumps(RepList_msq)):<{HEADER_LENGTH}}".encode('utf-8')
                    Client_Socket.send(RepList_msq_header + pickle.dumps(RepList_msq))
                RepList.clear()
                Executed = False
            servmsg = receive_message_client()

            # Mensagem automatica enquanto nao receber nenhuma mensagem
            if servmsg is False:
                print(f'{ProcID} -> Não recebeu nada ainda')
                raise RuntimeError()

            # Se recebeu uma mensagem do tipo de requisicao, executa o primeiro da fila de requisicoes
            if int(servmsg['qualMsg']) == REQUEST:
                # Se a secao critica nao estiver sendo executada, avisa que ja esta sendo executada
                # e o processo sera adicionado na lista
                if Executing:
                    for rep in RepList:
                        if rep['veioDe'] == servmsg['veioDe']:
                            print (f"Pedido de {rep['veioDe']} já na lista")
                            raise RuntimeError()
                    RepList.append(servmsg)
                    print(f"{ProcID} -> Adicionando na lista o processo ({ProcID}) e executando a secao critica")
                    
                # Senao, executa a secao critica
                else:
                    if Requested and (ProcTime < servmsg['procTemp'] or servmsg['horario'] > RequestedTime):
                        RepList.append(servmsg)
                        print(f"{ProcID} -> Adicionando a lista {servmsg['veioDe']} ja que o processo ({ProcID}) tem maior prioridade")
                    else:
                        print(f"{ProcID} -> Enviando resposta para {servmsg['veioDe']} para sua requisicao em: {servmsg['horario']}")
                        rep_msq= {
                            'qualMsg': REPLY, 
                            'foiPara': servmsg['veioDe']
                            }
                        rep_msq_header = f"{len(pickle.dumps(rep_msq)):<{HEADER_LENGTH}}".encode('utf-8')
                        Client_Socket.send(rep_msq_header + pickle.dumps(rep_msq))
            
            # Se recebeu uma mensagem do tipo de envio, executa a fila de envio
            if int(servmsg['qualMsg']) == SENT:
                print(f"{ProcID} -> Pedido enviado para: {servmsg['contaEnvio']}; de: {ProcID}")
                ReqList_count=servmsg['contaEnvio']
            
            # Se recebeu uma mensagem do tipo de resposta, executa a fila de respostas
            if int(servmsg['qualMsg']) == REPLY:
                print(f"{ProcID} -> Resposta recebida no: {ProcID}")
                ReqList.append(servmsg)
                if ReqList_count == len(ReqList):
                    print(f"{ProcID} -> Respostas recebidas dos processos: "+str(ReqList_count)+"")
                    ReqList_count -= len(ReqList)
                    if (ReqList_count == 0):
                        msg_exec= {
                            'qualMsg': EXEC, 
                            'veioDe': ProcID, 
                            'horario': logicalClock()
                            }
                        msg_header = f"{len(pickle.dumps(msg_exec)):<{HEADER_LENGTH}}".encode('utf-8')
                        Client_Socket.send(msg_header + pickle.dumps(msg_exec))
                        ecs = executeCS()
                        if ecs and len(RepList) > 0:
                            Executed = True
                            
            if int(servmsg['qualMsg']) == EXEC:
                print(f"{ProcID} -> {servmsg['veioDe']} esta utilizando a secao critica no tempo: {servmsg['horario']}")


    # Se ocorrer um erro, avisa o processo que ocorreu e encerra o programa
    except IOError as e:
        if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
            print('\nReading error: {}'.format(str(e)))
            sys.exit()
        continue
    
    except RuntimeError as e:
        continue

    except Exception as e:
        print('\nReading error: '.format(str(e)))
        sys.exit()