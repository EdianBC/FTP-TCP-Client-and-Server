import socket
import re
import os

class FTPClient:
    def __init__(self, host, port=21):
        self.host = host
        self.port = port
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket.settimeout(3)

    def connect(self):
        """Conecta al servidor FTP."""
        self.control_socket.connect((self.host, self.port))
        return self.read_response()

    def read_response(self):
        """Lee la respuesta del servidor FTP."""
        response = ''
        while True:
            part = self.control_socket.recv(1024).decode()
            response += part
            if response.endswith('\r\n') or len(part) < 1024:
                break
        return response

    def send_command(self, command):
        """Envía un comando al servidor FTP y devuelve la respuesta."""
        self.control_socket.sendall(f"{command}\r\n".encode())
        return self.read_response()

    def login(self, username='anonymous', password='anonymous@'):
        """Autentica al usuario en el servidor FTP."""
        print(self.send_command(f'USER {username}'))
        return self.send_command(f'PASS {password}')

    def pasv_mode(self):
        """Establece el modo PASV para la transferencia de datos."""
        response = self.send_command('PASV')
        ip_port_pattern = re.compile(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)')
        ip_port_match = ip_port_pattern.search(response)
        if ip_port_match:
            ip_address = '.'.join(ip_port_match.groups()[:4])
            port = (int(ip_port_match.group(5)) << 8) + \
                int(ip_port_match.group(6))
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_socket.connect((ip_address, port))
            return data_socket
        else:
            print("PASV mode setup failed.")
            return None
        
    def active_mode(self):
        """Establece el modo activo para la transferencia de datos."""
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.bind(('', 0))
        data_socket.listen(1)
        data_socket_ip, data_socket_port = data_socket.getsockname()
        ip_parts = data_socket_ip.split('.')
        port_parts = [str(data_socket_port >> 8), str(data_socket_port & 0xFF)]
        port_command = f"{','.join(ip_parts)},{','.join(port_parts)}"
        response = self.send_command(f'PORT {port_command}')
        if response.startswith('200'):
            return data_socket
        else:
            print("Active mode setup failed.")
            return None

    def list_files(self, directory="."):
        """Lista los archivos en el directorio especificado, devolviendo una lista con la distinción entre archivos y carpetas."""
        try:
            data_socket = self.pasv_mode()
            if data_socket is None:
                print("No se pudo establecer una conexión de datos.")
                return
            self.send_command(f'LIST {directory}')
            data_response = ""
            while True:
                data_part = data_socket.recv(4096).decode()
                if not data_part:
                    break
                data_response += data_part
            data_socket.close()
            print(self.read_response())

            return data_response
    
        except Exception as e:
            print(f"Error al listar archivos: {e}")

    def simple_list_files(self, directory="."):
        """Lista los archivos en el directorio especificado, devolviendo una lista con los nombres de los archivos."""
        try:
            data_socket = self.pasv_mode()
            if data_socket is None:
                print("No se pudo establecer una conexión de datos.")
                return
            self.send_command(f'NLST {directory}')
            data_response = ""
            while True:
                data_part = data_socket.recv(4096).decode()
                if not data_part:
                    break
                data_response += data_part
            data_socket.close()
            print(self.read_response())

            return data_response
    
        except Exception as e:
            print(f"Error al listar archivos: {e}")

    def change_directory(self, path):
        """Cambia el directorio actual en el servidor FTP."""
        return self.send_command(f'CWD {path}')
    
    def change_directory_up(self):
        """Cambia al directorio padre."""
        return self.send_command('CDUP')

    def make_directory(self, dirname):
        """Crea un nuevo directorio en el servidor FTP."""
        return self.send_command(f'MKD {dirname}')

    def remove_directory(self, dirname):
        """Elimina un directorio en el servidor FTP."""
        return self.send_command(f'RMD {dirname}')

    def delete_file(self, filename):
        """Intenta eliminar un archivo."""
        return self.send_command(f'DELE {filename}')

    def rename_file(self, from_name, to_name):
        """Renombra un archivo en el servidor FTP."""
        self.send_command(f'RNFR {from_name}')
        return self.send_command(f'RNTO {to_name}')

    def retrieve_file(self, filename, local_filename=''):
        """Descarga un archivo del servidor FTP."""

        if not local_filename:
            local_filename = filename

        data_socket = self.pasv_mode()
        if not data_socket:
            return "Error estableciendo modo PASV."
        
        server_ans = self.send_command(f'RETR {filename}')

        if server_ans.startswith('550'):
            return f"Error, file '{filename}' not found."

        with open(local_filename, 'wb') as file:
            while True:
                data = data_socket.recv(1024)
                if not data:
                    break
                file.write(data)
        data_socket.close()
        return self.read_response()

    def store_file(self, local_filename, filename=''):
        """Sube un archivo al servidor FTP."""
        if not filename:
            filename = local_filename

        file_path = os.path.abspath(os.path.join(os.getcwd(), local_filename))
        
        if not os.path.exists(file_path):
            return f"Error, file '{file_path}' not found."
        
        data_socket = self.pasv_mode()
        if not data_socket:
            return "Error estableciendo modo PASV."
        
        self.send_command(f'STOR {filename}')
        with open(local_filename, 'rb') as file:
            while True:
                data = file.read(1024)
                if not data:
                    break
                data_socket.sendall(data)
        
        data_socket.close()
        return self.read_response()
    
    def store_unique_file(self, local_filename, filename=''):
        """Sube un archivo al servidor FTP con un nombre único."""
        if not filename:
            filename = local_filename

        file_path = os.path.abspath(os.path.join(os.getcwd(), local_filename))
        
        if not os.path.exists(file_path):
            return f"Error, file '{file_path}' not found."
        
        data_socket = self.pasv_mode()
        if not data_socket:
            return "Error estableciendo modo PASV."
        
        self.send_command(f'STOU {filename}')
        with open(local_filename, 'rb') as file:
            while True:
                data = file.read(1024)
                if not data:
                    break
                data_socket.sendall(data)
        
        data_socket.close()
        return self.read_response()
    
    def append_file(self, local_filename, filename=''):
        """Añade un archivo al servidor FTP."""
        if not filename:
            filename = local_filename

        file_path = os.path.abspath(os.path.join(os.getcwd(), local_filename))
        
        if not os.path.exists(file_path):
            return f"Error, file '{file_path}' not found."
        
        data_socket = self.pasv_mode()
        if not data_socket:
            return "Error estableciendo modo PASV."
        
        self.send_command(f'APPE {filename}')
        with open(local_filename, 'rb') as file:
            while True:
                data = file.read(1024)
                if not data:
                    break
                data_socket.sendall(data)
        
        data_socket.close()
        return self.read_response()


    def print_working_directory(self):
        """Imprime el directorio de trabajo actual en el servidor FTP."""
        return self.send_command('PWD')
    
    def system(self):
        """Devuelve el sistema operativo del servidor FTP."""
        return self.send_command('SYST')
    
    def help(self):
        """Devuelve la lista de comandos soportados por el servidor FTP."""
        return self.send_command('HELP')
    
    def noop(self):
        """Comando NOOP."""
        return self.send_command('NOOP')
    
    def status(self):
        """Devuelve el estado de la conexión con el servidor FTP."""
        return self.send_command('STAT')
    
    def abort(self): #wtf asi y ya??
        """Aborta la transferencia de datos."""
        return self.send_command('ABOR')

    def account_info(self, account_info): 
        """Envía la información de la cuenta al servidor FTP."""
        return self.send_command(f'ACCT {account_info}')
    
    def set_download_start_position(self, position):
        """Establece la posición de inicio para la descarga de archivos."""
        return self.send_command(f'REST {position}')

    def site_command(self, command):
        """Envía un comando SITE al servidor FTP."""
        return self.send_command(f'SITE {command}')
    
    def allocate_space(self, bytes):
        """Reserva espacio en el servidor FTP."""
        return self.send_command(f'ALLO {bytes}')
    
    def structure_mount(self, path):
        """Monta una estructura en el servidor FTP."""
        return self.send_command(f'STRU {path}')
    
    def reinitialize(self):
        """Reinicia la conexión con el servidor FTP."""
        return self.send_command('REIN')

    def file_structure(self, structure):
        """Establece la estructura de un archivo."""
        return self.send_command(f'STRU {structure}')
    
    def transfer_mode(self, mode):
        """Establece el modo de transferencia."""
        return self.send_command(f'MODE {mode}')
    
    def file_type(self, type):
        """Establece el tipo de archivo."""
        return self.send_command(f'TYPE {type}')

    def quit(self):
        """Cierra la sesión y la conexión con el servidor FTP."""
        response = self.send_command('QUIT')
        self.control_socket.close()
        return response


if __name__ == "__main__":
    # ftp = FTPClient('127.0.0.1')
    # print(ftp.connect())
    # print(ftp.login('user1', 'password1'))

    ftp = FTPClient('ftp.dlptest.com')
    print(ftp.connect())
    print(ftp.login('dlpuser', 'rNrKYTX9g7z3RgJRmxWuGHbeu'))

    # ftp = FTPClient('test.rebex.net')
    # print(ftp.connect())
    # print(ftp.login('demo', 'password'))

    while True:
        try:
            user_input = input("ftp>> ")

            command_parts = user_input.strip().split(" ")
            command = command_parts[0].lower()
            args = command_parts[1:]

            if command == 'ls':
                print(ftp.list_files(*args))
            elif command == 'nls':
                print(ftp.simple_list_files(*args))
            elif command == 'cd':
                print(ftp.change_directory(*args))
            elif command == 'cdup':
                print(ftp.change_directory_up(*args))
            elif command == 'pwd':
                print(ftp.print_working_directory(*args))
            elif command == 'mkdir':
                print(ftp.make_directory(*args))
            elif command == 'rd':
                print(ftp.remove_directory(*args))
            elif command == 'rf':
                print(ftp.delete_file(*args))
            elif command == 'rename':
                print(ftp.rename_file(*args))
            elif command == 'dow':
                print(ftp.retrieve_file(*args))
            elif command == 'upl':
                print(ftp.store_file(*args))
            elif command == 'uplu':
                print(ftp.store_unique_file(*args))
            elif command == 'app':
                print(ftp.append_file(*args))
            elif command == 'sys':
                print(ftp.system(*args))
            elif command == 'help':
                print(ftp.help(*args))
            elif command == 'noop':
                print(ftp.noop(*args))
            elif command == 'stat':
                print(ftp.status(*args))
            elif command == 'abort':
                print(ftp.abort(*args))
            elif command == 'acct':
                print(ftp.account_info(*args))
            elif command == 'rest':
                print(ftp.set_download_start_position(*args))
            elif command == 'site':
                print(ftp.site_command(*args))
            elif command == 'allo':
                print(ftp.allocate_space(*args))
            elif command == 'stru':
                print(ftp.structure_mount(*args))
            elif command == 'rein':
                print(ftp.reinitialize(*args))
            elif command == 'stru':
                print(ftp.file_structure(*args))
            elif command == 'mode':
                print(ftp.transfer_mode(*args))
            elif command == 'type':
                print(ftp.file_type(*args))
            elif command == 'quit':
                print(ftp.quit(*args))
                break
            else:
                print("Comando no reconocido. Por favor, inténtelo de nuevo.")
        except Exception as e:
            print(f"Error: {e}")
