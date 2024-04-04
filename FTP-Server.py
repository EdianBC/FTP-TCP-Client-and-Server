import socket
import os
import re
import threading
from termcolor import colored as col


class FTPServer:
    def __init__(self, host='', port=21):
        self.host = host
        self.port = port
        self.data_port = 0
        
        self.users = {'user1': 'password1'}  
        
        self.storage_folder = 'FTP_Storage'
        self.root_dir = os.path.join(os.getcwd(), self.storage_folder)
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
        
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket.bind((self.host, self.port))
        self.control_socket.listen(5)
        
        print(col(f'Servidor FTP iniciado en {self.host}:{self.port}',"green"))


    # To implement
    # #  USER <SP> <username> <CRLF>
    # #  PASS <SP> <password> <CRLF>
    #  ACCT <SP> <account-information> <CRLF>
    #  CWD <SP> <pathname> <CRLF>
    #  CDUP <CRLF>
    #  SMNT <SP> <pathname> <CRLF>
    #  QUIT <CRLF>
    #  REIN <CRLF>
    #  PORT <SP> <host-port> <CRLF>
    # #  PASV <CRLF>
    #  TYPE <SP> <type-code> <CRLF>
    #  STRU <SP> <structure-code> <CRLF>
    #  MODE <SP> <mode-code> <CRLF>
    #  RETR <SP> <pathname> <CRLF>
    # #  STOR <SP> <pathname> <CRLF>
    #  STOU <CRLF>
    #  APPE <SP> <pathname> <CRLF>
    #  ALLO <SP> <decimal-integer>
    #  [<SP> R <SP> <decimal-integer>] <CRLF>
    #  REST <SP> <marker> <CRLF>
    #  RNFR <SP> <pathname> <CRLF>
    #  RNTO <SP> <pathname> <CRLF>
    #  ABOR <CRLF>
    #  DELE <SP> <pathname> <CRLF>
    #  RMD <SP> <pathname> <CRLF>
    #  MKD <SP> <pathname> <CRLF>
    #  PWD <CRLF>
    #  LIST [<SP> <pathname>] <CRLF>
    #  NLST [<SP> <pathname>] <CRLF>
    #  SITE <SP> <string> <CRLF>
    #  SYST <CRLF>
    #  STAT [<SP> <pathname>] <CRLF>
    #  HELP [<SP> <string>] <CRLF>
    #  NOOP <CRLF>
        
    def USER(self, username):
        if username in self.users:
            self.conn.sendall(b'331 User name okay, need password\r\n')
        else:
            self.conn.sendall(b'530 User incorrect in\r\n')

    def PASS(self,username, password):
        if self.users.get(username) == password:
            self.conn.sendall(b'230 User logged in, proceed\r\n')
            return True
        else:
            self.conn.sendall(b'530 Password incorrect in\r\n')
            return False
        
    def ACCT(self, account_information):
        pass

    def CWD(self, new_dir):
        if os.path.isdir(new_dir):
            self.conn.sendall(b'250 Directory successfully changed.\r\n')
            return new_dir
        else:
            self.conn.sendall(b'550 Failed to change directory.\r\n')


    def CDUP(self):
        pass

    def SMNT(self, pathname):
        pass

    def REIN(self):
        pass

    def PORT(self, host_port):
        pass

    def PASV(self):
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_socket.bind((self.host, 0))
        self.data_port = self.data_socket.getsockname()[1]
        self.data_socket.listen(1)
        print(self.host)
        host_bytes = self.host.split('.')
        port_bytes = [self.data_port // 256, self.data_port % 256]
        self.conn.sendall(f'227 Entering Passive Mode ({host_bytes[0]},{host_bytes[1]},{host_bytes[2]},{host_bytes[3]},{port_bytes[0]},{port_bytes[1]})\r\n'.encode())

    def TYPE(self, type_code):
        pass

    def STRU(self, structure_code):
        pass

    def MODE(self, mode_code):
        pass

    def RETR(self, pathname):
        pass

    def STOR(self, file_path):
        try:
            self.conn.sendall(b'150 File status okay; about to open data connection.\r\n')
            data_conn, _ = self.data_socket.accept()

            with open(file_path, 'wb') as file:
                while True:
                    up_data = data_conn.recv(1024)
                    if not up_data:
                        break
                    file.write(up_data)

                data_conn.close()
                self.conn.sendall(b'226 Transfer complete.\r\n')

        except Exception as e:
            self.conn.sendall(b'550 Failed to store file.\r\n')
            print(f'Error storing file: {e}')
            if data_conn:
                data_conn.close()
    
    def STOU(self):
        pass

    def APPE(self, pathname):
        pass

    def ALLO(self, decimal_integer):
        pass

    def REST(self, marker):
        pass

    def RNFR(self, pathname):
        pass

    def RNTO(self, pathname):
        pass

    def ABOR(self):
        pass

    def DELE(self, file_path):
        try:
            os.remove(file_path)
            self.conn.sendall(b'250 File deleted successfully.\r\n')
        except Exception as e:
            self.conn.sendall(b'550 Failed to delete file.\r\n')
            print(f'Error deleting file: {e}')

    def RMD(self, target_dir):
        try:
            os.rmdir(target_dir)
            self.conn.sendall(b'250 Directory deleted successfully.\r\n')
        except Exception as e:
            self.conn.sendall(b'550 Failed to delete directory.\r\n')
            print(f'Error deleting directory: {e}')

    def MKD(self, new_dir):
        try:
            os.mkdir(new_dir)
            self.conn.sendall(b'257 Directory created successfully.\r\n')
        except Exception as e:
            self.conn.sendall(b'550 Failed to create directory.\r\n')
            print(f'Error creating directory: {e}')

    def PWD(self,current_dir):
        relative_dir = os.path.relpath(current_dir, os.path.join(os.getcwd(), self.storage_folder))
        self.conn.sendall(f"257 '{relative_dir}'\r\n".encode())
        

    def LIST(self, current_dir, extra_dir):
        try:
            self.conn.sendall(b'150 Here comes the directory listing\r\n')
            data_conn, _ = self.data_socket.accept()
            dir_list = '\n'.join(os.listdir(os.path.join(current_dir, extra_dir))) + '\r\n'
            data_conn.sendall(dir_list.encode())
            data_conn.close()
            self.conn.sendall(b'226 Directory send OK\r\n')
        except Exception as e:
            self.conn.sendall(f'550 Failed to list directory: {e}\r\n'.encode())
            print(f'Error listing directory: {e}')
            if data_conn:
                data_conn.close()

    def NLST(self, pathname):
        pass

    def SITE(self, string):
        pass

    def SYST(self):
        pass

    def STAT(self, pathname):
        pass

    def HELP(self, string):
        pass

    def NOOP(self):
        pass

    



    def handle_client(self, conn, addr):
        print(col(f'Conexión entrante de {addr}',"green"))
        conn.sendall(b'220 Welcome to the FTP server\r\n')

        authenticated = False
        username = ''
        current_dir = self.root_dir

        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break
                print(f'Received: {data.strip()}')

                command = data.split()[0].upper()

                if command == 'USER':
                    username = data.split()[1]
                    self.USER(username)

                elif command == 'PASS':
                    password = data.split()[1]
                    authenticated=self.PASS(username,password)

                elif not authenticated:
                    conn.sendall(b'530 Not logged in\r\n')
                    continue

                elif command == 'PASV':
                    self.PASV()

                elif command == 'PWD':
                    self.PWD(current_dir)

                elif command == 'LIST':                        
                    extra_dir = data.split()[1]
                    self.LIST(current_dir, extra_dir)

                elif command == 'CWD':
                    path = data.split()[1]
                    new_dir = os.path.abspath(os.path.join(current_dir, path))
                    current_dir = self.CWD(new_dir)

                elif command == 'MKD':
                    dirname = data.split()[1]
                    new_dir = os.path.abspath(os.path.join(current_dir, dirname))
                    self.MKD(new_dir)

                elif command == 'RMD':
                    dirname = data.split()[1]
                    target_dir = os.path.abspath(os.path.join(current_dir, dirname))
                    self.RMD(target_dir)


                elif command == 'DELE':
                    filename = data.split()[1]
                    file_path = os.path.abspath(os.path.join(current_dir, filename))
                    self.DELE(file_path)

                elif command == 'RNFR':
                    from_name = data.split()[1]
                    from_path = os.path.abspath(os.path.join(current_dir, from_name))

                    conn.sendall(b'350 Ready for RNTO.\r\n')

                    data = conn.recv(1024).decode()
                    if not data:
                        conn.sendall(b'500 Syntax error, command unrecognized.\r\n')
                    elif data.split()[0] != 'RNTO':
                        conn.sendall(b'500 Syntax error, command unrecognized.\r\n')
                    else:
                        
                        to_name = data.split()[1]
                        to_path = os.path.abspath(os.path.join(current_dir, to_name))

                        try:
                            os.rename(from_path, to_path)
                            conn.sendall(b'250 File renamed successfully.\r\n')
                        except Exception as e:
                            conn.sendall(b'550 Failed to rename file.\r\n')
                            print(f'Error renaming file: {e}')


                elif command == 'RETR':
                    filename = data.split()[1]
                    file_path = os.path.abspath(os.path.join(current_dir, filename))

                    if not os.path.exists(file_path):
                        #conn.sendall(b'550 Failed to retrieve file.\r\n')
                        #conn.sendall(b'550 Failed to retrieve file.\r\n')
                        print(f"Error: File '{file_path}' not found")
                        continue
                    
                    try:  
                        conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                        data_conn, _ = self.data_socket.accept()

                        with open(file_path, 'rb') as file:
                            while True:
                                down_data = file.read(1024)
                                if not down_data:
                                    break
                                data_conn.sendall(down_data)
                                
                        data_conn.close()
                        conn.sendall(b'226 Transfer complete.\r\n')

                    except Exception as e:
                        conn.sendall(b'550 Failed to retrieve file.\r\n')
                        print(f'Error retrieving file: {e}')
                        if data_conn:
                            data_conn.close()
                        


                elif command == 'STOR':
                    filename = data.split()[1]
                    file_path = os.path.abspath(os.path.join(current_dir, filename))
                    self.STOR(file_path)
                    
                elif command == 'QUIT':
                    conn.sendall(b'221 Goodbye\r\n')
                    break
        
                else:
                    conn.sendall(b'502 Command not implemented\r\n')
            


            except Exception as e:
                print(f'Error: {e}')
                conn.sendall(b'500 Syntax error, command unrecognized\r\n')
                continue

        conn.close()

    def start(self):
        while True:
            self.conn, self.addr = self.control_socket.accept()
            threading.Thread(target=self.handle_client, args=(self.conn, self.addr)).start()



            

if __name__ == "__main__":
    ftp_server = FTPServer(host='127.0.0.1')
    ftp_server.start()
