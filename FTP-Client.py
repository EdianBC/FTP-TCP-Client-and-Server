import socket
import re

class FTPClient:

    def __init__(self, host, port=21):
        self.host = host
        self.port = port
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def quit(self):
        """Envía el comando QUIT para cerrar la sesión y cierra el socket."""
        try:
            response = self.send_command('QUIT')
            self.control_socket.close()
            return response
        except Exception as e:
            print(f"Error al cerrar la conexión: {e}")

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
            if len(part) < 1024:
                break
        return response

    def send_command(self, command):
        """Envía un comando al servidor FTP y devuelve la respuesta."""
        self.control_socket.send(f"{command}\r\n".encode())
        return self.read_response()

    def login(self, username='anonymous', password='anonymous@'):
        """Autentica al usuario en el servidor FTP."""
        self.send_command(f'USER {username}')
        return self.send_command(f'PASS {password}')

    def pasv_mode(self):
        """Establece el modo PASV para la transferencia de datos."""
        response = self.send_command('PASV')
        ip_port_pattern = re.compile(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)')
        ip_port_match = ip_port_pattern.search(response)
        if ip_port_match:
            ip_address = '.'.join(ip_port_match.groups()[:4])
            port = (int(ip_port_match.group(5)) << 8) + int(ip_port_match.group(6))
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_socket.connect((ip_address, port))
            return data_socket
        else:
            raise Exception("PASV mode setup failed.")

    def list_files(self, directory="."):
        """Lista los archivos en el directorio especificado."""
        data_socket = self.pasv_mode()
        self.send_command(f'LIST {directory}')
        files = data_socket.recv(4096).decode()
        data_socket.close()
        return files

    def change_directory(self, path):
        """Cambia el directorio actual en el servidor FTP."""
        return self.send_command(f'CWD {path}')

    def make_directory(self, dirname):
        """Crea un nuevo directorio en el servidor FTP."""
        return self.send_command(f'MKD {dirname}')

    def remove_directory(self, dirname):
        """Elimina un directorio en el servidor FTP."""
        return self.send_command(f'RMD {dirname}')

    def delete_file(self, filename):
        """Elimina un archivo en el servidor FTP."""
        return self.send_command(f'DELE {filename}')

    def rename_file(self, from_name, to_name):
        """Renombra un archivo en el servidor FTP."""
        self.send_command(f'RNFR {from_name}')
        return self.send_command(f'RNTO {to_name}')

    def retrieve_file(self, filename, local_filename):
        """Descarga un archivo del servidor FTP."""
        data_socket = self.pasv_mode()
        self.send_command(f'RETR {filename}')
        with open(local_filename, 'wb') as file:
            while True:
                data = data_socket.recv(1024)
                if not data:
                    break
                file.write(data)
        data_socket.close()
        return "Archivo descargado exitosamente."

    def store_file(self, local_filename, filename):
        """Sube un archivo al servidor FTP."""
        try:
            data_socket = self.pasv_mode()
        except Exception as e:
            print(e)
            return "Fallo al establecer la conexión de datos en modo PASV."
        
        self.send_command(f'STOR {filename}')
        with open(local_filename, 'rb') as file:
            data = file.read(1024)
            while data:
                data_socket.send(data)
                data = file.read(1024)
        data_socket.close()
        return "Archivo subido exitosamente."


if __name__ == "__main__":
    ftp = FTPClient('ftp.dlptest.com')
    print(ftp.connect())
    print(ftp.login('dlpuser', 'rNrKYTX9g7z3RgJRmxWuGHbeu'))
    ftp.store_file("README.md","README.md")
    print(ftp.list_files())
    print(ftp.quit())
