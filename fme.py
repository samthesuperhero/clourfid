"""
Module for message exchange via files.
Benefits:
- fully async
- messages can queue for long time, as messages are in files
- atomic write so no read crashes
- two sided communication
Nagatives:
- not tested for high load
"""
import os
import os.path
from json import loads, dumps
import hashlib
import zlib
from time import time

class FileMessageExchange:
    """ Class FileMessageExchange to exchange messages via files in folders, atomically """
    def __init__(self, own_instance_id_set, msg_dir_path_set, message_types_set):
        """
        Initializing class:
        own_instance_id_set - string, own name with which to send and receive messages,
        important that user choose name always by his own, so there are no general
        checks that the name is used by anybody else; otherwise more than one instance
        or process can send and receive by this same name and there can be a sync problem
        then.
        msg_dir_path_set - directory in which the file messages put, stored and read
        from.
        message_types_set - list of strings each strictly of 3 symbols length, describing
        allowed message types in communication.
        """
        assert isinstance(own_instance_id_set, str), "Type of own_instance_id_set not str()"
        assert own_instance_id_set != str(), "own_instance_id_set can not be empty and must be at least 1 symbol length"
        assert not any((__idx in set('[]')) for __idx in own_instance_id_set), "own_instance_id_set can not contain [ or ]"
        assert isinstance(message_types_set, list), "message_types_set must be list()"
        self.__err = str()
        self.__own_id = own_instance_id_set
        self.__msg_dir_path = msg_dir_path_set
        self.__list_dicts_rcv = list()
        self.__text_encoding = "utf-8"
        self.__message_types_available = message_types_set
    def snd(self, snd_to_id, msgtype_to_send, dict_data_to_snd, msgtype_static_name=""):
        """
        Method snd() to send the message through file.
        If you need to set file name explicitly use msgtype_to_send = "STATIC",
        and pass file name in the optional msgtype_static_name parameter,
        not shorter than 3 letters length.
        """
        self.__err = str()
        if not isinstance(msgtype_to_send, str):
            self.__err = "Type of msgtype_to_send not str()"
            return -1
        if not isinstance(snd_to_id, str):
            self.__err = "Type of snd_to_id not str()"
            return -1
        if any((__idx in set('[]')) for __idx in snd_to_id):
            self.__err = "snd_to_id can not contain [ or ]"
            return -1
        if snd_to_id == str():
            self.__err = "snd_to_id can not be empty and must be at least 1 symbol length"
            return -1
        if (msgtype_to_send != "STATIC") and (msgtype_to_send not in self.__message_types_available):
            self.__err = "msgtype_to_send = '" + msgtype_to_send + "' unknown"
            return -1
        if (msgtype_to_send == "STATIC") and (not isinstance(msgtype_static_name, str)):
            self.__err = "Type of msgtype_static_name not str()"
            return -1
        if (msgtype_to_send == "STATIC") and (len(msgtype_static_name) < 3):
            self.__err = "msgtype_static_name len less than 3 letters: " + msgtype_static_name
            return -1
        if not isinstance(dict_data_to_snd, dict):
            self.__err = "Type of dict_data_to_snd not dict()"
            return -1
        # Create payload dict()
        __dict_payload_data = dict()
        __dict_payload_data["type"] = msgtype_to_send
        __dict_payload_data["data"] = dict_data_to_snd
        __temp_hashlib = hashlib.md5()
        __temp_hashlib.update(dumps(dict_data_to_snd, skipkeys=True).encode(self.__text_encoding))
        __temp_hashlib_hash = __temp_hashlib.digest()
        __dict_payload_data["md5"] = str().join(format(__tmp_x0, '02x') for __tmp_x0 in __temp_hashlib_hash)
        __dict_payload_data_to_file = dumps(__dict_payload_data, skipkeys=True).encode(self.__text_encoding)
        del __temp_hashlib, __temp_hashlib_hash
        # Loop to check filenames for existence,
        # if there is a file with just created filename,
        # go for next loop.
        # But it should always be unique, this is more to
        # be on the safe side.
        while True:
            # Create filename
            __msg_file_name = str()
            if msgtype_to_send != "STATIC":
                __msg_file_name += "R"                  # prefix of real message, 1 symbol
                __tmp_time = time()
                __tmp_time_int = str(int(__tmp_time))
                if len(__tmp_time_int) != 10:
                    self.__err = "Error getting timestamp int = '" + __tmp_time_int + "'"
                    return -1
                __tmp_time_frc = (str(round(__tmp_time % 1, 6))[2:]).zfill(6)
                __msg_file_name += __tmp_time_int       # timestamp seconds, 10 symbols
                __msg_file_name += __tmp_time_frc       # timestamp microsesonds, 6 symbols
                __msg_file_name += msgtype_to_send      # type of message, 3 symbols
                del __tmp_time, __tmp_time_int, __tmp_time_frc
                __msg_contents_crc32 = "{0:02x}".format(zlib.crc32(__dict_payload_data_to_file)).zfill(8)
                __msg_file_name += __msg_contents_crc32 # CRC32 of message contents, 8 symbols
                __msg_file_name += "[" + self.__own_id + "]"    # from, not less than 3 symbols
                __msg_file_name += "[" + snd_to_id + "]"        # to, not less than 3 symbols
                __msg_file_name_left_crc32 = "{0:02x}".format(zlib.crc32(__msg_file_name.encode('ascii'))).zfill(8)
                __msg_file_name += __msg_file_name_left_crc32   # CRC32 of message name, 8 symbols
                __msg_file_name += ".json"
                del __msg_contents_crc32, __msg_file_name_left_crc32
            else:
                __msg_file_name = msgtype_static_name
            # Create temp filename to write contents on disk
            __msg_file_name_temp = "*" + __msg_file_name[1:]
            # Atomically write the file http://docs.python.org/library/os.html#os.rename
            # https://stackoverflow.com/questions/2333872/atomic-writing-to-file-with-python
            # http://stackoverflow.com/questions/7433057/is-rename-without-fsync-safe
            try:
                if not os.access(self.__msg_dir_path + "/" + __msg_file_name_temp, os.F_OK):
                    __msg_file = open(self.__msg_dir_path + "/" + __msg_file_name_temp, 'wb')
                    __msg_file.write(__dict_payload_data_to_file)
                    __msg_file.flush()
                    os.fsync(__msg_file.fileno())
                    __msg_file.close()
                    break
            except Exception:
                self.__err = "Error writing file " + self.__msg_dir_path + "/" + __msg_file_name
                if os.access(self.__msg_dir_path + "/" + __msg_file_name_temp, os.F_OK):
                    try:
                        os.remove(self.__msg_dir_path + "/" + __msg_file_name_temp)
                    except Exception:
                        self.__err += " Error erasing file " + self.__msg_dir_path + "/" + __msg_file_name
                        return -1
                return -1
        try:
            os.rename(self.__msg_dir_path + "/" + __msg_file_name_temp, self.__msg_dir_path + "/" + __msg_file_name)
        except Exception:
            self.__err = "Error os.rename() on file " + self.__msg_dir_path + "/" + __msg_file_name
            if os.access(self.__msg_dir_path + "/" + __msg_file_name_temp, os.F_OK):
                try:
                    os.remove(self.__msg_dir_path + "/" + __msg_file_name_temp)
                except Exception:
                    self.__err += " Error erasing file " + self.__msg_dir_path + "/" + __msg_file_name
                    return -1
            if os.access(self.__msg_dir_path + "/" + __msg_file_name, os.F_OK):
                try:
                    os.remove(self.__msg_dir_path + "/" + __msg_file_name)
                except Exception:
                    self.__err += " Error erasing file " + self.__msg_dir_path + "/" + __msg_file_name
                    return -1
            return -1
        return 0
    def rcv(self, rcv_from_id, msgtype_to_recv, msgtype_static_name="", erase_after_read=True, cutoff_time=None):
        """
        Method rcv() to receive all messages from the rcv folder.
        In rcv_from_id please set the ID of sender, the rcv_from_id = "*" is reserved,
        this will mean that messages from any sender sent to this receiver will be received.
        Or if you need to receive only 1 static message,
        sent by snd() with msgtype_to_send = "STATIC",
        put file name in msgtype_static_name and set msgtype_to_recv = "STATIC",
        rcv_from_id in this case is ignored.
        If you set cutoff_time it must be float() setting the timestamp in UTC
        meaning the earliest time after which messages are received. All messages
        after this time are got from files but ignored, so the information in such
        messages is lost and can not be recovered.
        """
        self.__err = str()
        __time_of_msg = float()
        if not isinstance(msgtype_to_recv, str):
            self.__err = "Type of msgtype_to_recv not str()"
            return -1
        if (msgtype_to_recv != "STATIC") and (msgtype_to_recv not in self.__message_types_available):
            self.__err = "msgtype_to_recv = '" + msgtype_to_recv + "' unknown"
            return -1
        if (msgtype_to_recv == "STATIC") and (not isinstance(msgtype_static_name, str)):
            self.__err = "Type of msgtype_static_name not str()"
            return -1
        if (msgtype_to_recv == "STATIC") and (len(msgtype_static_name) < 3):
            self.__err = "msgtype_static_name len less than 3 letters: " + msgtype_static_name
            return -1
        if msgtype_to_recv != "STATIC":
            if not isinstance(rcv_from_id, str):
                self.__err = "Type of rcv_from_id not str()"
                return -1
            if rcv_from_id == str():
                self.__err = "rcv_from_id can not be empty and must be at least 1 symbol length"
                return -1
            if any((__idx in set('[]')) for __idx in rcv_from_id):
                self.__err = "rcv_from_id can not contain [ or ]"
                return -1
        if (cutoff_time is not None) and (not isinstance(cutoff_time, float)):
            self.__err = "cutoff_time must be None or float: " + repr(cutoff_time)
            return -1
        cutoff_time_value = float()
        if isinstance(cutoff_time, float):
            cutoff_time_value = cutoff_time
        __files_in_dir_list = list()
        __rcv_mes_count = int()
        for __tmp_root, __tmp_dirs, __tmp_files in os.walk(self.__msg_dir_path):
            for __tmp_name_walk_f in __tmp_files:
                if msgtype_to_recv != "STATIC":
                    __files_in_dir_list.append((__tmp_name_walk_f, os.path.join(__tmp_root, __tmp_name_walk_f)))
                else:
                    if __tmp_name_walk_f == msgtype_static_name:
                        __files_in_dir_list.append((__tmp_name_walk_f, os.path.join(__tmp_root, __tmp_name_walk_f)))
        if (msgtype_to_recv == "STATIC") and (len(__files_in_dir_list) > 1):
            self.__err = "Sync problem for STATIC read, found " + str(len(__files_in_dir_list)) + " files with name '" + msgtype_static_name + "'"
            return -1
        # Loop through all files with needed type of message
        for __tmp_file_tuple in __files_in_dir_list:
            __filename_ok_flag = True
            if msgtype_to_recv != "STATIC":
                # First we check all conditions on file name before opening,
                # and only if all OK and we confirmed that this is the right message
                # for us, we open file
                try:
                    __filename_ok_flag *= (len(__tmp_file_tuple[0]) >= 47)
                    __filename_ok_flag *= (__tmp_file_tuple[0][0] == "R")
                    __filename_ok_flag *= (__tmp_file_tuple[0][-5:].lower() == ".json")
                    __filename_ok_flag *= (__tmp_file_tuple[0].count("[") == 2)
                    __filename_ok_flag *= (__tmp_file_tuple[0].count("]") == 2)
                    __filename_ok_flag *= (__tmp_file_tuple[0].count("][") == 1)
                    __filename_ok_flag *= (__tmp_file_tuple[0][28] == "[")
                    __filename_ok_flag *= (__tmp_file_tuple[0][-14] == "]")
                    __find_delimeter = __tmp_file_tuple[0].find("][")
                    __filename_ok_flag *= (__find_delimeter >= 30)
                    __filename_ok_flag *= (__find_delimeter <= (len(__tmp_file_tuple[0]) - 17))
                    __file_msg_from = __tmp_file_tuple[0][29:__find_delimeter]
                    __file_msg_to = __tmp_file_tuple[0][(__find_delimeter + 2):-14]
                    if rcv_from_id != "*":  # Don't theck the sender if rcv_from_id = "*"
                        __filename_ok_flag *= (__file_msg_from == rcv_from_id)
                    __filename_ok_flag *= (__file_msg_to == self.__own_id)
                    __time_int = float(__tmp_file_tuple[0][1:11])
                    __time_frc = float(__tmp_file_tuple[0][11:17]) / 1000000
                    __time_of_msg = __time_int + __time_frc
                    del __time_int, __time_frc
                    __filename_ok_flag *= (__tmp_file_tuple[0][17:20] == msgtype_to_recv)
                    __filename_crc32_for_data = int(__tmp_file_tuple[0][20:28], 16)
                    __filename_ok_flag *= (int(__tmp_file_tuple[0][-13:-5], 16) == zlib.crc32(__tmp_file_tuple[0][:-13].encode('ascii')))
                except Exception:
                    __filename_ok_flag = False
            if __filename_ok_flag:
                __file_check_ok_flag = True
                try:
                    __msg_file = open(__tmp_file_tuple[1], 'rb')
                except Exception:
                    __file_check_ok_flag = False
                try:
                    __data_from_msg_file = __msg_file.read()
                    __data_from_msg_file_dict = loads(__data_from_msg_file, encoding=self.__text_encoding)
                    if __data_from_msg_file_dict["type"] != msgtype_to_recv:
                        __file_check_ok_flag = False
                except Exception:
                    __file_check_ok_flag = False
                try:
                    __msg_file.close()
                except Exception:
                    __file_check_ok_flag = False
                if not isinstance(__data_from_msg_file_dict["data"], dict):
                    self.__err = "Type of __data_from_msg_file_dict['data'] not dict()"
                    return -1
                if msgtype_to_recv == "STATIC":
                    __filename_crc32_for_data = zlib.crc32(__data_from_msg_file)
                if zlib.crc32(__data_from_msg_file) == __filename_crc32_for_data:
                    try:
                        __hash_message_payload = bytes(bytearray.fromhex(__data_from_msg_file_dict["md5"]))
                        __temp_hashlib = hashlib.md5()
                        __temp_hashlib.update(dumps(__data_from_msg_file_dict["data"], skipkeys=True).encode(self.__text_encoding))
                        if __hash_message_payload != __temp_hashlib.digest():
                            __file_check_ok_flag = False
                    except Exception:
                        __file_check_ok_flag = False
                # If file contents and file name passed all checks,
                # get the message payload data to self.__list_dicts_rcv
                if __file_check_ok_flag:
                    if cutoff_time is None or __time_of_msg >= cutoff_time_value:
                        self.__list_dicts_rcv.append((__data_from_msg_file_dict["data"], __time_of_msg, __file_msg_from))
                        __rcv_mes_count += 1
                # And erase the file if the flag is set
                if erase_after_read:
                    try:
                        if os.access(__tmp_file_tuple[1], os.F_OK):
                            os.remove(__tmp_file_tuple[1])
                    except Exception:
                        self.__err = "Error erasing file " + __tmp_file_tuple[1]
                        return -1
        return __rcv_mes_count
    def clearall(self):
        """ Flush the list of incoming messages """
        self.__err = str()
        self.__list_dicts_rcv = list()
    def getall(self, clear_received=True):
        """
        Return full list of tuples with received messages
        """
        self.__err = str()
        __list_dicts_rcv_return = self.__list_dicts_rcv
        if clear_received:
            self.__list_dicts_rcv = list()
        return __list_dicts_rcv_return
    def getold(self, clear_received=True):
        """
        Return the oldest tuple with the oldest message received,
        if receive list is empty, returns tuple = ("null", -1)
        """
        self.__err = str()
        __msg_tuple_return = min(self.__list_dicts_rcv, key=lambda __key: __key[1], default=("null", -1, ""))
        if (__msg_tuple_return != ("null", -1, "")) and clear_received:
            __msg_tuple_return_idx = self.__list_dicts_rcv.index(__msg_tuple_return)
            return self.__list_dicts_rcv.pop(__msg_tuple_return_idx)
        elif __msg_tuple_return == ("null", -1, ""):
            return list()
        return __msg_tuple_return
    def set_msg_types(self, msg_types_to_set):
        """ Set list of available message types """
        self.__err = str()
        __set_msg_types_res = int()
        if not isinstance(msg_types_to_set, list):
            self.__err = "msg_types_to_set type not a list()"
            return -1
        for __tmp_list_item in msg_types_to_set:
            if not isinstance(__tmp_list_item, str):
                self.__err = "One or more items of msg_types_to_set type not an str()"
                return -1
            if len(__tmp_list_item) != 3:
                self.__err = "Item '" + __tmp_list_item + "' of msg_types_to_set is wrong, len() != 3"
                return -1
        self.__message_types_available = msg_types_to_set
        return __set_msg_types_res
    def geterr(self):
        """ Get error description if returned -1 """
        return self.__err
