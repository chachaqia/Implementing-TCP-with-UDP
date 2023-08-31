"""
    Sample code for Receiver
    Python 3
    Usage: python3 receiver.py receiver_port sender_port FileReceived.txt flp rlp
    coding: utf-8

    Notes:
        Try to run the server first with the command:
            python3 receiver_template.py 9000 10000 FileReceived.txt 1 1
        Then run the sender:
            python3 sender_template.py 11000 9000 FileToReceived.txt 1000 1

    Author: Rui Li (Tutor for COMP3331/9331)
"""
# here are the libs you may find it useful:
import datetime, time  # to calculate the time delta of packet transmission
import logging, sys  # to write the log
import socket  # Core lib, to send packet via UDP socket
from threading import Thread  # (Optional)threading will make the timer easily implemented
import random  # for flp and rlp function

BUFFERSIZE = 10000


class Receiver:
    def __init__(self, receiver_port: int, sender_port: int, filename: str, flp: float, rlp: float) -> None:
        '''
        The server will be able to receive the file from the sender via UDP
        :param receiver_port: the UDP port number to be used by the receiver to receive PTP segments from the sender.
        :param sender_port: the UDP port number to be used by the sender to send PTP segments to the receiver.
        :param filename: the name of the text file into which the text sent by the sender should be stored
        :param flp: forward loss probability, which is the probability that any segment in the forward direction (Data, FIN, SYN) is lost.
        :param rlp: reverse loss probability, which is the probability of a segment in the reverse direction (i.e., ACKs) being lost.

        '''
        self.address = "127.0.0.1"  # change it to 0.0.0.0 or public ipv4 address if want to test it between different computers
        self.receiver_port = int(receiver_port)
        self.sender_port = int(sender_port)
        self.server_address = (self.address, self.receiver_port)
        self.filename = filename
        self.flp = flp
        self.rlp = rlp
        self.relative_0 = 0
        self.data_buffer = dict()

        # init the UDP socket
        # define socket for the server side and bind address
        logging.debug(f"The sender is using the address {self.server_address} to receive message!")
        self.receiver_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.receiver_socket.bind(self.server_address)
        pass

    def run(self) -> None:
        '''
        This function contain the main logic of the receiver
        '''
        while True:
            # try to receive any incoming message from the sender
            incoming_message, sender_address = self.receiver_socket.recvfrom(BUFFERSIZE)

            # randomly drop the packet
            flp = int(float(self.flp) * 100)
            if random.randint(1, 100) < flp:
                logging.debug("drop the package!")
                continue

            type_no_int = int.from_bytes(incoming_message[0: 2], byteorder='big')

            if type_no_int == 2:
                logging.debug(f"client{sender_address} send a SYN!")
                ISN = int(incoming_message[2:12].decode('utf-8'))
                ACK_type_no = 1
                ACK_seq_no = ISN + 1
                self.relative_0 = ACK_seq_no
                reply_message = ACK_type_no.to_bytes(2, "big") + bytes(str(ACK_seq_no), 'utf-8').zfill(10) + b""
                rlp = int(float(self.rlp) * 100)
                if random.randint(1, 100) < rlp:
                    logging.debug(f"drop the ACK {ACK_seq_no}!")
                    continue
                self.receiver_socket.sendto(reply_message, sender_address)

            elif type_no_int == 0:
                # save data into the buffer
                seq_no_int = int(incoming_message[2:12].decode('utf-8'))
                logging.debug(f"client{sender_address} send a message: type_no = {type_no_int} sequence = {seq_no_int % 65536}"
                              f" len = {len(incoming_message[12:].decode('utf-8'))}")
                data = incoming_message[12:].decode('utf-8')
                self.data_buffer[int((seq_no_int - self.relative_0)/1000)] = data

                # reply the ACK
                ACK_type_no = 1
                ACK_seq_no = seq_no_int + len(incoming_message[12:].decode('utf-8'))
                reply_message = ACK_type_no.to_bytes(2, "big") + bytes(str(ACK_seq_no), 'utf-8').zfill(10) + b""

                rlp = int(float(self.rlp) * 100)
                if random.randint(1, 100) < rlp:
                    logging.debug(f"drop the ACK {ACK_seq_no}!")
                    continue
                self.receiver_socket.sendto(reply_message, sender_address)

            elif type_no_int == 3:
                logging.debug(f"client{sender_address} send a FIN!")
                FIN = int(incoming_message[2:12].decode('utf-8'))
                ACK_type_no = 1
                ACK_seq_no = FIN + 1
                self.relative_0 = ACK_seq_no
                reply_message = ACK_type_no.to_bytes(2, "big") + bytes(str(ACK_seq_no), 'utf-8').zfill(10) + b""
                rlp = int(float(self.rlp) * 100)
                if random.randint(1, 100) < rlp:
                    logging.debug(f"drop the ACK {ACK_seq_no}!")
                    continue
                self.receiver_socket.sendto(reply_message, sender_address)
                with open(self.filename, 'w') as f:
                    for i in range(len(self.data_buffer)):
                        f.write(self.data_buffer[i])
                break
            elif type_no_int == 4:
                break


if __name__ == '__main__':
    # logging is useful for the log part: https://docs.python.org/3/library/logging.html
    logging.basicConfig(
        # filename="Receiver_log.txt",
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(asctime)s,%(msecs)03d %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S')

    if len(sys.argv) != 6:
        print(
            "\n===== Error usage, python3 receiver.py receiver_port sender_port FileReceived.txt flp rlp ======\n")
        exit(0)

    receiver = Receiver(*sys.argv[1:])
    receiver.run()

