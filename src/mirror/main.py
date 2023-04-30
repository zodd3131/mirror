import socket
import os
import sys
import logging
import threading
import signal
import argparse
from typing import List
from queue import Queue
from prometheus_client import Counter
from prometheus_client import Histogram
from prometheus_client import start_http_server
from mirror.tcp_client import ClientThread

# Prometheus variables declaration
SIZE = Histogram('size_data_bytes', 'Data sent',['server'])
MESSAGE = Counter('message_count', 'number of message received',['server'])

class Main():
    def __init__(self, port: int, clients: List[str]) -> None:
        self.logger = logging.getLogger(__name__)
        self.threads: List[threading.Thread] = []
        self.conn: socket.socket = None
        self.port = port
        self.clients = clients

    def run(self) -> None:
        queues: List[Queue] = []
        self.threads: List[ClientThread] = []
        for index, uri in enumerate(self.clients):
            queues.append(Queue())
            self.threads.append(ClientThread(uri, queues[index]))

        # create an INET, STREAMing socket
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        try:
            # bind the socket to a public host, and a well-known port
            serversocket.bind(('0.0.0.0', self.port))
        except OSError:
            self.logger.fatal(f"socket already in use")
            sys.exit(1)
        # become a server socket
        serversocket.listen()
        # accept connections from outside
        self.logger.info("Waiting for incoming connection ...")
        self.conn, address = serversocket.accept()
        self.logger.info(f"Incoming connection from {address}")
        # now do something with the serversocket
        for thread in self.threads:
            thread.start()
        while True:
            data = self.conn.recv(16384)
            if not data:
                self.stop()
                break
            self.logger.debug(f"data received {len(data)}bytes")
            MESSAGE.labels(server=address).inc()
            SIZE.labels(server=address).observe(len(data))
            for index, queue in enumerate(queues):
                self.logger.debug(f"add data to queue server{index}")
                queue.put(data)

    def stop(self) -> None:
        """
        method to stop all thread started by run
        """
        self.logger.info("connection is closing")
        self.conn.close()
        for client in self.threads:
            client.stop()
        self.logger.info("connection closed")
        self.logger.info("Exiting program")
        sys.exit(1)

if __name__ == '__main__':
    class ServiceExit(Exception):
        """
        Custom exception which is used to trigger the clean exit
        of all running threads and the main program.
        """

    def service_shutdown(signum, frame):
        """
        Function to raise ServiceExit, called when signal SIGTERM is caught
        """
        raise ServiceExit

        # SIGTERM and SIGKILL are signals sent by docker engine
    signal.signal(signal.SIGTERM, service_shutdown)
    # Argument parsing

    parser = argparse.ArgumentParser(description='Mirror TCP connection.')
    parser.add_argument('clients', metavar='host:port', type=str, nargs='+',
                        help='a client address to send messages to')
    parser.add_argument('-p', '--port', action='store', type=int, help='listening port')

    args = parser.parse_args()

    # Logging configuration
    loglevel = os.environ.get("LOG_LEVEL","info")
    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)


    main = Main(args.port, args.clients)
    # Start up the server to expose the metrics.
    start_http_server(8000)
    try:
        main.run()
    except ServiceExit:
        main.stop()