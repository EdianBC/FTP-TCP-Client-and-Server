import socket
import os
import re
import threading

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
        
        print(f'Servidor FTP iniciado en {self.host}:{self.port}')

    def handle_client(self, conn, addr):
        print(f'Conexión entrante de {addr}')
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
                    if username in self.users:
                        conn.sendall(b'331 User name okay, need password\r\n')
                    else:
                        conn.sendall(b'530 User incorrect in\r\n')
                elif command == 'PASS':
                    password = data.split()[1]
                    if self.users.get(username) == password:
                        authenticated = True
                        conn.sendall(b'230 User logged in, proceed\r\n')
                    else:
                        conn.sendall(b'530 Password incorrect in\r\n')
                elif not authenticated:
                    conn.sendall(b'530 Not logged in\r\n')


                elif command == 'PASV':
                    self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.data_socket.bind((self.host, 0))
                    self.data_port = self.data_socket.getsockname()[1]
                    self.data_socket.listen(1)
                    print(self.host)
                    host_bytes = self.host.split('.')
                    port_bytes = [self.data_port // 256, self.data_port % 256]
                    conn.sendall(f'227 Entering Passive Mode ({host_bytes[0]},{host_bytes[1]},{host_bytes[2]},{host_bytes[3]},{port_bytes[0]},{port_bytes[1]})\r\n'.encode())


                elif command == 'PWD':
                    relative_dir = os.path.relpath(current_dir, os.path.join(os.getcwd(), self.storage_folder))
                    conn.sendall(f"257 '{relative_dir}'\r\n".encode())


                elif command == 'LIST':    
                    try:
                        extra_dir = data.split()[1]
                        conn.sendall(b'150 Here comes the directory listing\r\n')
                        data_conn, _ = self.data_socket.accept()
                        dir_list = '\n'.join(os.listdir(os.path.join(current_dir, extra_dir))) + '\r\n'
                        data_conn.sendall(dir_list.encode())
                        data_conn.close()
                        conn.sendall(b'226 Directory send OK\r\n')
                    except Exception as e:
                        conn.sendall(f'550 Failed to list directory: {e}\r\n'.encode())
                        print(f'Error listing directory: {e}')
                        if data_conn:
                            data_conn.close()



                elif command == 'CWD':
                    path = data.split()[1]
                    new_dir = os.path.abspath(os.path.join(current_dir, path))

                    if os.path.isdir(new_dir):
                        current_dir = new_dir
                        conn.sendall(b'250 Directory successfully changed.\r\n')
                    else:
                        conn.sendall(b'550 Failed to change directory.\r\n')


                elif command == 'MKD':
                    dirname = data.split()[1]
                    new_dir = os.path.abspath(os.path.join(current_dir, dirname))

                    try:
                        os.mkdir(new_dir)
                        conn.sendall(b'257 Directory created successfully.\r\n')
                    except Exception as e:
                        conn.sendall(b'550 Failed to create directory.\r\n')
                        print(f'Error creating directory: {e}')


                elif command == 'RMD':
                    dirname = data.split()[1]
                    target_dir = os.path.abspath(os.path.join(current_dir, dirname))

                    try:
                        os.rmdir(target_dir)
                        conn.sendall(b'250 Directory deleted successfully.\r\n')
                    except Exception as e:
                        conn.sendall(b'550 Failed to delete directory.\r\n')
                        print(f'Error deleting directory: {e}')


                elif command == 'DELE':
                    filename = data.split()[1]
                    file_path = os.path.abspath(os.path.join(current_dir, filename))

                    try:
                        os.remove(file_path)
                        conn.sendall(b'250 File deleted successfully.\r\n')
                    except Exception as e:
                        conn.sendall(b'550 Failed to delete file.\r\n')
                        print(f'Error deleting file: {e}')

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

                    except FileNotFoundError:
                        conn.sendall(b'550 File not found.\r\n')

                    except Exception as e:
                        conn.sendall(b'550 Failed to retrieve file.\r\n')
                        print(f'Error retrieving file: {e}')
                    
                    if data_conn:
                        data_conn.close()
                        


                elif command == 'STOR':
                    filename = data.split()[1]
                    file_path = os.path.abspath(os.path.join(current_dir, filename))

                    try:
                        conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                        data_conn, _ = self.data_socket.accept()
                        with open(file_path, 'wb') as file:
                            while True:
                                up_data = data_conn.recv(1024)
                                if not up_data:
                                    break
                                file.write(up_data)

                        data_conn.close()
                        conn.sendall(b'226 Transfer complete.\r\n')

                    except Exception as e:
                        conn.sendall(b'550 Failed to store file.\r\n')
                        print(f'Error storing file: {e}')
                    
                    if data_conn:
                        data_conn.close()


                elif command == 'QUIT':
                    conn.sendall(b'221 Goodbye\r\n')
                    break
                

                else:
                    conn.sendall(b'502 Command not implemented\r\n')
            


            except Exception as e:
                print(f'Error: {e}')
                conn.sendall(b'500 Syntax error, command unrecognized\r\n')
                break

        conn.close()

    def start(self):
        while True:
            conn, addr = self.control_socket.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    ftp_server = FTPServer(host='127.0.0.1')
    ftp_server.start()
