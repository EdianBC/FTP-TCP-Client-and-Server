import socket
import os
import re
import threading

class FTPServer:
    def __init__(self, host='', port=21):
        self.host = host
        self.port = port
        self.data_port = 0
        self.users = {'user1': 'password1'}  # Añade tus usuarios y contraseñas aquí
        self.root_dir = os.getcwd()
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
                    conn.sendall(f'257 "{current_dir}"\r\n'.encode())
                
                #Maybe use os.path.join ?
                elif command == 'LIST':
                    extra_dir = data.split()[1]
                    conn.sendall(b'150 Here comes the directory listing\r\n')
                    data_conn, _ = self.data_socket.accept()
                    dir_list = '\n'.join(os.listdir(current_dir + '\\' + extra_dir)) + '\r\n'
                    data_conn.sendall(dir_list.encode())
                    data_conn.close()
                    conn.sendall(b'226 Directory send OK\r\n')
                

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
                        # Enviar un mensaje de error si no se pudo eliminar el directorio
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

                    # Espera el comando RNTO del cliente
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
                        with open(file_path, 'rb') as file:
                    
                            conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                            data_conn, _ = self.data_socket.accept()

                            while True:
                                down_data = file.read(1024)
                                if not data:
                                    break
                                data_conn.sendall(down_data)

                            data_conn.close()
                            conn.sendall(b'226 Transfer complete.\r\n')

                    except FileNotFoundError:
                        conn.sendall(b'550 File not found.\r\n')

                    except Exception as e:
                        conn.sendall(b'550 Failed to retrieve file.\r\n')
                        print(f'Error retrieving file: {e}')


                elif command == 'STOR':
                    filename = data.split()[1]
                    file_path = os.path.abspath(os.path.join(current_dir, filename))

                    try:
                        with open(file_path, 'wb') as file:
                            conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                            data_conn, _ = self.data_socket.accept()

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



# import socket
# import os

# class FTP_Server:
#     def __init__(self, host='', port=21):
#         self.host = host
#         self.port = port
#         self.cwd = os.path.abspath(os.getcwd()) 
#         self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.socket.bind((self.host, self.port))
#         self.socket.listen(5)
#         print(f"Servidor FTP corriendo en {self.host}:{self.port}")
#         self.data_socket = None

#     def start_data_socket(self):
#         """Inicia un socket de datos en un puerto aleatorio para el modo PASV."""
#         self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.data_socket.bind((self.host, 0))  # 0 significa que el SO elige el puerto (creo xd)
#         self.data_socket.listen(1)
#         data_port = self.data_socket.getsockname()[1]
#         return data_port

#     def handle_pasv(self, client_socket):
#         data_port = self.start_data_socket()
#         ip_addr = self.host.replace('.', ',')
#         p1 = data_port // 256
#         p2 = data_port % 256
#         response = f'227 Entering Passive Mode ({ip_addr},{p1},{p2}).\r\n'
#         client_socket.sendall(response.encode('utf-8'))

#     def handle_client(self, client_socket):
#         client_socket.sendall(b'220 (pyFTPd 0.1)\r\n')
#         while True:
#             cmd = client_socket.recv(1024).decode('utf-8').strip()
#             if not cmd:
#                 break
#             print(f"Comando recibido: {cmd}")
#             command, *args = cmd.split(' ')
            
#             if command == 'USER':
#                 username = args[0] if args else ''
#                 if username == 'user':
#                     client_socket.sendall(b'331 Username okay, need password.\r\n')
#                     password = client_socket.recv(1024).decode('utf-8').strip().split(' ')[1]
#                     if password == 'password':
#                         client_socket.sendall(b'230 User logged in, proceed.\r\n')
#                     else:
#                         client_socket.sendall(b'530 Not logged in.\r\n')
#                 else:
#                     client_socket.sendall(b'530 Not logged in.\r\n')
#                 continue

#             if command == 'PASV':
#                 # Tenemos que ahacer el PASV para el LIST
#                 client_socket.sendall(b'502 Command not implemented.\r\n')
#                 continue

#             if command == 'PWD':
#                 client_socket.sendall(self.cwd.encode('utf-8'))
#                 continue

#             if command == 'CWD':
#                 if args:
#                     new_dir=self.cwd
#                     if args[0] == "..":
#                         new_dir = os.path.abspath(os.path.join(self.cwd, '..'))
#                     else:
#                         new_dir = os.path.abspath(os.path.join(self.cwd, args[0]))
                    
#                     if os.path.isdir(new_dir):
#                         self.cwd = new_dir
#                         print(self.cwd)
#                         client_socket.sendall(b'250 Directory successfully changed.\r\n')
#                     else:
#                         client_socket.sendall(b'550 Failed to change directory.\r\n')
#                 else:
#                     client_socket.sendall(b'501 Syntax error in parameters or arguments.\r\n')
#                 continue

#             if command == 'QUIT':
#                 break
#             else:
#                 client_socket.sendall(b'500 Unknown command.\r\n')
#         client_socket.close()

#     def run(self):
#         try:
#             while True:
#                 client_socket, addr = self.socket.accept()
#                 print(f"Conexión aceptada de {addr}")
#                 self.handle_client(client_socket)
#         except KeyboardInterrupt:
#             print("Servidor cerrado.")
#         finally:
#             self.socket.close()

# if __name__ == '__main__':
#     ftp_server = FTP_Server(host='127.0.0.1', port=21)
#     ftp_server.run()
