"""
    Sample code for Sender (multi-threading)
    Python 3
    Usage: python3 sender.py receiver_port sender_port FileToSend.txt max_recv_win rto
    coding: utf-8

    Notes:
        Try to run the server first with the command:
            python3 receiver_template.py 9000 10000 FileReceived.txt 1 1
        Then run the sender:
            python3 sender_template.py 11000 9000 FileToReceived.txt 1000 1

    Author: Rui Li (Tutor for COMP3331/9331)
"""
# here are the libs you may find it useful:
import threading
import time  # to calculate the time delta of packet transmission
import logging, sys  # to write the log
import random
import socket  # Core lib, to send packet via UDP socket
from threading import Thread  # (Optional)threading will make the timer easily implemented

BUFFERSIZE = 10000


class Sender:
    def __init__(self, sender_port: int, receiver_port: int, filename: str, max_win: int, rot: int) -> None:
        '''
        The Sender will be able to connect the Receiver via UDP
        :param sender_port: the UDP port number to be used by the sender to send PTP segments to the receiver
        :param receiver_port: the UDP port number on which receiver is expecting to receive PTP segments from the sender
        :param filename: the name of the text file that must be transferred from sender to receiver using your reliable transport protocol.
        :param max_win: the maximum window size in bytes for the sender window.
        :param rot: the value of the retransmission timer in milliseconds. This should be an unsigned integer.
        '''
        self.sender_port = int(sender_port)
        self.receiver_port = int(receiver_port)
        self.sender_address = ("127.0.0.1", self.sender_port)
        self.receiver_address = ("127.0.0.1", self.receiver_port)
        self.filename = filename
        self.sender_contents = []
        self.ISN = random.randint(0, 2**16-1)
        self.SYN_successful = False
        self.FIN_successful = False
        self.windows_number = int(int(max_win) / 1000)
        self.rot = int(rot) / 1000
        self.send_win_buffer = dict()
        self.send_timers = dict()
        self.relative_0 = self.ISN + 1
        self.contents_dict = dict()
        self.last_data_len = 0
        self.initial_time = 0
        self.FIN_seq = self.relative_0 + 1
        self.amount_of_original_data = 0
        self.amount_of_data_segement_sent = 0
        self.amount_of_resnd_data_segement = 0
        self.amount_of_ack = 0

        # init the UDP socket
        # logging.debug(f"The sender is using the address {self.sender_address}")
        self.sender_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sender_socket.bind(self.sender_address)

        #  (Optional) start the listening sub-thread first
        self._is_active = True  # for the multi-threading

        self.send_win_lock = threading.Lock()
        self.send_timers_lock = threading.Lock()

        listen_thread = Thread(target=self.listen)
        listen_thread.start()
        # todo add codes here

    def ptp_open(self):
        # todo add/modify codes here
        # send a greeting message to receiver
        # message = "Greetings! COMP3331."
        # self.sender_socket.sendto(message.encode("utf-8"), self.receiver_address)
        type_no = 0
        seq_no = self.ISN + 1
        with open(self.filename, "rb") as file:
            while True:
                data = file.read(1000)
                if data:
                    content = type_no.to_bytes(2, "big") + bytes(str(seq_no), "utf-8").zfill(10) + data
                    self.sender_contents.append(content)
                    seq_no += 1000
                    self.FIN_seq += len(content[12:].decode('utf-8'))
                else:
                    break
                self.FIN_seq = self.FIN_seq % 65536

        self.last_data_len = len(self.sender_contents[-1][12:].decode('utf-8'))
        i = 0
        for send_content in self.sender_contents:
            self.contents_dict[i] = send_content
            i += 1

    def ptp_send(self):
        # todo add codes here
        for i in range(int(self.windows_number)):
            self.sender_socket.sendto(self.contents_dict[i], self.receiver_address)
            self.send_win_buffer[i] = self.contents_dict[i]
            seq_no = int(self.contents_dict[i][2:12].decode('utf-8'))
            data_len = len(self.contents_dict[i][12:])
            self.amount_of_original_data += data_len
            start_time = time.time()
            self.send_timers[i] = start_time
            logging.debug(f"snd    {round((start_time - self.initial_time)*1000, 2)}    DATA    {seq_no}    {data_len}")

        for j in range(int(self.windows_number), len(self.contents_dict)):
            while 1:
                # resend trigger
                with self.send_timers_lock:
                    for i in self.send_timers:
                        if time.time() - self.send_timers[i] > self.rot:
                            self.sender_socket.sendto(self.send_win_buffer[i], self.receiver_address)
                            seq_no = int(self.contents_dict[i][2:12].decode('utf-8'))
                            data_len = len(self.contents_dict[i][12:])
                            resend_time = time.time()
                            self.send_timers[i] = resend_time
                            logging.debug(f"snd    {round((resend_time - self.initial_time)*1000, 2)}    DATA    {seq_no % 65536}    {data_len}")
                            self.amount_of_resnd_data_segement += 1
                    if len(self.send_win_buffer) < self.windows_number:
                        self.sender_socket.sendto(self.contents_dict[j], self.receiver_address)
                        self.send_win_buffer[j] = self.contents_dict[j]
                        seq_no = int(self.contents_dict[j][2:12].decode('utf-8'))
                        data_len = len(self.contents_dict[j][12:])
                        self.amount_of_original_data += data_len
                        start_time = time.time()
                        self.send_timers[j] = start_time
                        logging.debug(f"snd    {round((start_time - self.initial_time) * 1000, 2)}    DATA    {seq_no % 65536}    {data_len}")
                        break
            # self.sender_socket.sendto(self.contents_dict[j], self.receiver_address)
            # with self.send_win_lock:
            #     self.send_win_buffer[j] = self.contents_dict[j]
            # seq_no = int(self.contents_dict[j][2:12].decode('utf-8'))
            # data_len = len(self.contents_dict[j][12:])
            # start_time = time.time()
            # with self.send_timers_lock:
            #     self.send_timers[j] = start_time
            # logging.debug(f"snd  {round((start_time - self.initial_time)*1000, 2)}    DATA  {seq_no}  {data_len}")

        if len(self.send_timers) > 0:
            while 1:
                with self.send_timers_lock:
                    for i in self.send_timers:
                        if time.time() - self.send_timers[i] > self.rot:
                            self.sender_socket.sendto(self.send_win_buffer[i], self.receiver_address)
                            seq_no = int(self.contents_dict[i][2:12].decode('utf-8'))
                            data_len = len(self.contents_dict[i][12:])
                            resend_time = time.time()
                            self.send_timers[i] = resend_time
                            logging.debug(f"snd    {round((resend_time - self.initial_time)*1000, 2)}    DATA    {seq_no}    {data_len}")
                            self.amount_of_resnd_data_segement += 1
                if len(self.send_timers) == 0:
                    break

        # for send_content in self.sender_contents:
        #     self.sender_socket.sendto(send_content, self.receiver_address)
        #     seq_no = int.from_bytes(send_content[2: 4], byteorder='big')
        #     data_len = len(send_content[4:])
        #     logging.debug(f"snd  Time    DATA  {seq_no}  {data_len}")
        #     time.sleep(0.5)

    def ptp_close(self):
        # todo add codes here
        self._is_active = False  # close the sub-thread
        # self.sender_socket.close()



    def listen(self):
        '''(Multithread is used)listen the response from receiver'''
        # logging.debug("Sub-thread for listening is running")
        while self._is_active:
            # todo add socket
            incoming_message, _ = self.sender_socket.recvfrom(BUFFERSIZE)
            type_no_int = int.from_bytes(incoming_message[0: 2], byteorder='big')
            if type_no_int == 1:
                self.amount_of_ack += 1
                seq_no_int = int(incoming_message[2:12].decode('utf-8'))
                if seq_no_int == self.relative_0:
                    self.SYN_successful = True
                    logging.debug(f"rcv    {round((time.time() - self.initial_time)*1000, 2)}    ACK    {seq_no_int % 65536}    0")
                elif (seq_no_int - self.relative_0) % 1000 == 0:
                    logging.debug(f"rcv    {round((time.time() - self.initial_time)*1000, 2)}    ACK    {seq_no_int % 65536}    0")
                    rm_num = 0
                    with self.send_win_lock:
                        for i in self.send_win_buffer:
                            if int(self.send_win_buffer[i][2:12].decode('utf-8')) == seq_no_int - 1000:
                                rm_num = i
                                break
                        self.send_win_buffer.pop(rm_num)
                        # print(self.send_win_buffer)
                        # print(rm_num)
                    with self.send_timers_lock:
                        self.send_timers.pop(rm_num)
                elif seq_no_int == self.FIN_seq + 1:
                    self.FIN_successful = True
                    logging.debug(f"rcv    {round((time.time() - self.initial_time)*1000, 2)}    ACK    {seq_no_int % 65536}    0")
                else:
                    logging.debug(f"rcv    {round((time.time() - self.initial_time)*1000, 2)}    ACK    {seq_no_int % 65536}    0")
                    rm_num = 0
                    with self.send_win_lock:
                        for i in self.send_win_buffer:
                            if int(self.send_win_buffer[i][2:12].decode('utf-8')) == seq_no_int - self.last_data_len:
                                rm_num = i
                                break
                        self.send_win_buffer.pop(rm_num)
                    with self.send_timers_lock:
                        self.send_timers.pop(rm_num)

    def run(self):
        '''
        This function contain the main logic of the receiver
        '''
        # todo add/modify codes here
        # send SYN and ensure it is limiter than 3 times
        type_no = 2
        seq_no = self.ISN
        content = type_no.to_bytes(2, "big") + bytes(str(seq_no), 'utf-8').zfill(10) + b""
        finished = False
        closed = False
        i = 0
        for i in range(3):
            self.sender_socket.sendto(content, self.receiver_address)
            start_time = time.time()
            self.initial_time = start_time
            logging.debug(f"snd    {round((start_time - self.initial_time) * 1000, 2)}    SYN    {self.ISN}    0")
            while 1:
                if time.time() - start_time > self.rot:
                    break
                if self.SYN_successful:
                    self.ptp_open()
                    self.ptp_send()
                    self.ptp_close()
                    self.SYN_successful = False
                    finished = True
                    break
            if finished:
                type_no = 3
                seq_no = self.FIN_seq
                content = type_no.to_bytes(2, "big") + bytes(str(seq_no), 'utf-8').zfill(10) + b""
                for j in range(3):
                    self.sender_socket.sendto(content, self.receiver_address)
                    close_time = time.time()
                    logging.debug(f"snd    {round((close_time - self.initial_time) * 1000, 2)}    FIN    {self.FIN_seq}    0")
                    while 1:
                        if time.time() - close_time > self.rot:
                            break
                        if self.FIN_successful:
                            self.amount_of_data_segement_sent = len(self.sender_contents)
                            logging.debug(
                                f"Amount of (original) Data Transferred (in bytes) (excluding retransmissions): {self.amount_of_original_data} bytes\n"
                                f"Number of Data Segments Sent (excluding retransmissions): {self.amount_of_data_segement_sent}\n"
                                f"Number of Retransmitted Data Segments: {self.amount_of_resnd_data_segement}\n"
                                f"Number of Duplicate Acknowledgements received: {self.amount_of_ack}")
                            closed = True
                            break
                    if closed:
                        break
                break

        if not self.SYN_successful:
            if i >= 2:
                type_no = 4
                seq_no = 0
                content = type_no.to_bytes(2, "big") + bytes(str(seq_no), 'utf-8').zfill(10) + b""
                self.sender_socket.sendto(content, self.receiver_address)
            self.ptp_close()


if __name__ == '__main__':
    # logging is useful for the log part: https://docs.python.org/3/library/logging.html
    logging.basicConfig(
        filename="Sender_log.txt",
        # stream=sys.stderr,
        level=logging.DEBUG,
        format='%(message)20s',
        datefmt='%Y-%m-%d:%H:%M:%S')

    if len(sys.argv) != 6:
        print(
            "\n===== Error usage, python3 sender.py sender_port receiver_port FileReceived.txt max_win rot ======\n")
        exit(0)

    sender = Sender(*sys.argv[1:])
    sender.run()
