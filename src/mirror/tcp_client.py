import socket
import select
import threading
import logging
from queue import Queue
import time

class ClientThread(threading.Thread):
    def __init__(self, address: str, my_queue: Queue) -> None:
        super(ClientThread, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.queue: Queue = my_queue
        self.daemon = True
        self.address: str = address
        self.socket = None
        self.logger.info(f"Init Thread {address} init done")
        
    def run(self) -> None:
        self.logger.info(f"Init Thread {self.address} started")
        address, _ , port = self.address.partition(":")
        while True:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            try:
                self.socket.connect((address,int(port)))
                self.logger.info(f"connection established with {address}:{port}")
            except:
                self.logger.debug(f"connection refused from {address}:{port}")
                self.queue.queue.clear()
                time.sleep(1)
            else:
                while True:
                    item = self.queue.get()
                    try:
                        sent = self.socket.send(item)
                        self.logger.debug(f"data sent to {address}:{port} -> result: {sent}")
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        self.logger.error(f"disconnection from {address}:{port}")
                        break
                    except TimeoutError:
                        self.logger.debug(f"Timeout attempting to connect to {address}:{port}")
                        break
            finally:
                self.logger.debug(f"closing connection{address}:{port}")
                self.socket.close()
    
    def stop(self):
        self.logger.info(f"Init Thread {self.address} connection closing")
        self.socket.close()