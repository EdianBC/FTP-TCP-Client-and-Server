import socket
import os
import threading
import stat
import time
import platform
import uuid
import shutil

class FTPServer:
    def __init__(self, host='', port=21):
        self.host = host
        self.port = port
        self.data_port = 0
        
        self.users = {'user1': 'password1'}  

        self.data_type = 'ASCII'
        self.restart_point = 0
        self.structure_type = 'File'
        self.mode = 'Stream'
        
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
                        conn.sendall(b'530 User incorrect\r\n')

                elif command == 'PASS':
                    password = data.split()[1]
                    if self.users.get(username) == password:
                        authenticated = True
                        conn.sendall(b'230 User logged in, have a good day\r\n')
                    else:
                        conn.sendall(b'530 Password incorrect in\r\n')

                elif not authenticated:
                    conn.sendall(b'530 Not logged in\r\n')

                elif command == 'PASV':
                    try:
                        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.data_socket.bind((self.host, 0))
                        self.data_port = self.data_socket.getsockname()[1]
                        self.data_socket.listen(1)
                        print(self.host)
                        host_bytes = self.host.split('.')
                        port_bytes = [self.data_port // 256, self.data_port % 256]
                        conn.sendall(f'227 Entering Passive Mode ({host_bytes[0]},{host_bytes[1]},{host_bytes[2]},{host_bytes[3]},{port_bytes[0]},{port_bytes[1]})\r\n'.encode())
                    except Exception as e:
                        conn.sendall(b'425 Can not open data connection\r\n')
                        print(f'Error entering passive mode: {e}')

                elif command == 'PORT':
                    try:
                        data = data.split()[1].split(',')
                        host = '.'.join(data[:4])
                        port = int(data[4]) * 256 + int(data[5])
                        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.data_socket.connect((host, port))
                        conn.sendall(b'200 PORT command successful\r\n')
                    except Exception as e:
                        conn.sendall(b'425 Can not open data connection\r\n')
                        print(f'Error opening data connection: {e}')

                elif command == 'PWD':
                    relative_dir = os.path.relpath(current_dir, os.path.join(os.getcwd(), self.storage_folder))
                    conn.sendall(f"257 '{relative_dir}'\r\n".encode())

                elif command == 'LIST':
                    try:
                        conn.sendall(b'150 Here comes the directory listing\r\n')
                        data_conn, _ = self.data_socket.accept()

                        # Obtener la lista de archivos en el directorio actual
                        files = os.listdir(current_dir)

                        # Obtener los detalles de cada archivo
                        file_details = ['Permissions  Links  Size           Last-Modified  Name']
                        for file in files:
                            stats = os.stat(os.path.join(current_dir, file))

                            # Convertir los detalles del archivo a la forma de salida de 'ls -l'
                            details = {
                                'mode': stat.filemode(stats.st_mode).ljust(11),
                                'nlink': str(stats.st_nlink).ljust(6),
                                'size': str(stats.st_size).ljust(5),
                                'mtime': time.strftime('%b %d %H:%M', time.gmtime(stats.st_mtime)).ljust(12),
                                'name': file
                            }
                            file_details.append('{mode}  {nlink} {size}          {mtime}   {name}'.format(**details))

                        # Enviar los detalles de los archivos
                        dir_list = '\n'.join(file_details) + '\r\n'
                        data_conn.sendall(dir_list.encode())
                        data_conn.close()
                        conn.sendall(b'226 Directory send OK\r\n')
                    except Exception as e:
                        conn.sendall(f'550 Failed to list directory: {e}\r\n'.encode())
                        print(f'Error listing directory: {e}')
                        if data_conn:
                            data_conn.close()  

                elif command == 'NLST':    
                    try:
                        conn.sendall(b'150 Here comes the directory listing\r\n')
                        extra_dir = data.split()[1]
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

                elif command == 'CDUP':
                    current_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
                    conn.sendall(b'200 Directory changed to parent directory.\r\n')

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

                    if not os.path.exists(file_path):
                        conn.sendall(b'550 File not found.\r\n')
                        print(f"Error: File '{file_path}' not found")
                        continue
                    
                    try:  
                        conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                        data_conn, _ = self.data_socket.accept()

                        # Open the file in binary mode for binary data type, and text mode for ASCII
                        mode = 'rb' if self.data_type == 'Binary' else 'r'
                        with open(file_path, mode) as file:
                            file.seek(self.restart_point)
                            self.restart_point = 0

                            while True:
                                down_data = file.read(1024)
                                if not down_data:
                                    break
                                if self.data_type == 'ASCII':
                                    down_data = down_data.encode()
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

                    try:
                        conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                        data_conn, _ = self.data_socket.accept()

                        mode = 'wb' if self.data_type == 'Binary' else 'w'
                        with open(file_path, mode) as file:
                            
                            while True:
                                up_data = data_conn.recv(1024)
                                if not up_data:
                                    break
                                if self.data_type == 'ASCII':
                                    up_data = up_data.decode()
                                file.write(up_data)

                        data_conn.close()
                        conn.sendall(b'226 Transfer complete.\r\n')

                    except Exception as e:
                        conn.sendall(b'550 Failed to store file.\r\n')
                        print(f'Error storing file: {e}')
                        if data_conn:
                            data_conn.close()

                elif command == 'STOU':
                    base_filename = data.split()[1]
                    unique_filename = f"{base_filename}_{str(uuid.uuid4())}"
                    file_path = os.path.abspath(os.path.join(current_dir, unique_filename))

                    try:
                        conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                        data_conn, _ = self.data_socket.accept()

                        mode = 'wb' if self.data_type == 'Binary' else 'w'
                        with open(file_path, mode) as file:
                            
                            while True:
                                up_data = data_conn.recv(1024)
                                if not up_data:
                                    break
                                if self.data_type == 'ASCII':
                                    up_data = up_data.decode()
                                file.write(up_data)

                        data_conn.close()
                        response = f'226 Transfer complete. Unique filename: {unique_filename}\r\n'
                        conn.sendall(response.encode())

                    except Exception as e:
                        conn.sendall(b'550 Failed to store file.\r\n')
                        print(f'Error storing file: {e}')
                        if data_conn:
                            data_conn.close()

                elif command == 'APPE':
                    filename = data.split()[1]
                    file_path = os.path.abspath(os.path.join(current_dir, filename))

                    try:
                        conn.sendall(b'150 File status okay; about to open data connection.\r\n')
                        data_conn, _ = self.data_socket.accept()

                        # Open the file in append mode
                        mode = 'ab' if self.data_type == 'Binary' else 'a'
                        with open(file_path, mode) as file:
                            while True:
                                up_data = data_conn.recv(1024)
                                if not up_data:
                                    break
                                if self.data_type == 'ASCII':
                                    up_data = up_data.decode()
                                file.write(up_data)

                        data_conn.close()
                        conn.sendall(b'226 Transfer complete.\r\n')

                    except Exception as e:
                        conn.sendall(b'550 Failed to append to file.\r\n')
                        print(f'Error appending to file: {e}')
                        if data_conn:
                            data_conn.close()

                elif command == 'ABOR':
                    conn.sendall(b'502 Command not implemented\r\n')

                elif command == 'ALLO':
                    conn.sendall(b'202 No storage allocation necessary.\r\n')

                elif command == 'REST':
                    self.restart_point = int(data.split()[1])
                    response = f'350 Restarting at {self.restart_point}. Send STORE or RETRIEVE to initiate transfer.\r\n'
                    conn.sendall(response.encode())

                elif command == 'REIN':
                    authenticated = False
                    username = ''
                    self.data_type = 'ASCII'
                    self.restart_point = 0
                    self.structure_type = 'File'
                    self.mode = 'Stream'
                    conn.sendall(b'220 Service ready for new user.\r\n')
                    
                elif command == 'HELP':
                    conn.sendall(b'214-The following commands are recognized.\r\n')
                    conn.sendall(b'USER PASS PASV PWD LIST NLST CWD MKD RMD DELE RNFR RNTO RETR STOR TYPE NOOP SYST STAT HELP QUIT\r\n')
                    conn.sendall(b'214 Help OK.\r\n')

                elif command == 'NOOP':
                    conn.sendall(b'200 OK\r\n')
 
                elif command == 'SYST':
                    system_name = platform.system()
                    response = f'215 {system_name} Type: L8\r\n'
                    conn.sendall(response.encode())

                elif command == 'STAT':
                    response = '211-FTP Server Status\r\n'
                    response += f'Current directory: {current_dir}\r\n'
                    response += 'Connected to server\r\n'
                    response += '211 End of status\r\n'
                    conn.sendall(response.encode())

                elif command == 'ACCT':
                    response = '211-Account Status\r\n'
                    response += f'Name: {username}\r\n'
                    response += f'Password: {self.users[username]}\r\n'
                    response += '211 End of account status\r\n'
                    conn.sendall(response.encode())

                elif command == 'TYPE':
                    data_type = data.split()[1]
                    if data_type == 'A':
                        self.data_type = 'ASCII'
                        conn.sendall(b'200 Type set to ASCII.\r\n')
                    elif data_type == 'I':
                        self.data_type = 'Binary'
                        conn.sendall(b'200 Type set to Binary.\r\n')
                    else:
                        conn.sendall(b'504 Type not implemented.\r\n')

                elif command == 'SMNT':
                    conn.sendall(b'202 Structure mount not implemented.\r\n')

                elif command == 'STRU':
                    structure_type = data.split()[1]
                    if structure_type == 'F':
                        self.structure_type = 'File'
                        conn.sendall(b'200 File structure set to F.\r\n')
                    elif structure_type == 'R':
                        conn.sendall(b'504 Record structure not implemented.\r\n')
                    elif structure_type == 'P':
                        conn.sendall(b'504 Page structure not implemented.\r\n')
                    else:
                        conn.sendall(b'504 Structure not implemented.\r\n')

                elif command == 'MODE':
                    mode_type = data.split()[1]
                    if mode_type == 'S':
                        self.mode = 'Stream'
                        conn.sendall(b'200 Mode set to S.\r\n')
                    elif mode_type == 'B':
                        conn.sendall(b'504 Block mode not implemented.\r\n')
                    elif mode_type == 'C':
                        conn.sendall(b'504 Compressed mode not implemented.\r\n')
                    else:
                        conn.sendall(b'504 Mode not implemented.\r\n')
                    
                elif command == 'SITE':
                    site_command = data.split()[1]
                    if site_command == 'RFR':
                        folder_path = data.split()[2]
                        folder_path = os.path.abspath(os.path.join(current_dir, folder_path))

                        try:
                            shutil.rmtree(folder_path)
                            conn.sendall(b'250 Folder deleted successfully.\r\n')
                        except Exception as e:
                            conn.sendall(b'550 Failed to delete folder.\r\n')
                            print(f'Error deleting folder: {e}')
                    else:
                        conn.sendall(b'504 Command not implemented.\r\n')

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
