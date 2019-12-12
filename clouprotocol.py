"""
clouprotocol
Module with all needed definitions from Hopeland Technologies
proprietary protocol documentation.
Consists of classes, needed data and constants to work with Clou protocol.
"""
from os import access as os_access
from os import F_OK as os_F_OK
from re import findall as re_findall
from json import load
from time import strftime, gmtime, time

# --- Frame ---
# |0xAA|control word|Serial device address|Data length|Data|Calibration code|
# |0xAA|2byte|1byte|2byte(U16)|Nbyte|2byte|

class ClouProtocolDefinitions:
    """ Constants of Clou protocol """
    def __init__(self):
        """ Initializing all constants """
        self.RS485_USED = 1      # for RS485
        self.RS485_NOT_USED = 0  # if other interface used
        self.INIT_BY_READER = 1  # initiated by reader
        self.INIT_BY_USER = 0    # initiated by user PC or other device
        self.TYPE_ERR_WARN = 0           # 0, Reader error or warning message
        self.TYPE_CONF_MANAGE = 1        # 1, Reader configuration and management message
        self.TYPE_CONF_OPERATE = 2       # 2, RFID Configuration and operation message
        self.TYPE_LOG = 3                # 3, Reader log message
        self.TYPE_APP_UPGRADE = 4        # 4, Reader app processor software / baseband software upgrade message
        self.TYPE_TEST = 5               # 5, Testing command
        # Error types
        self.ERR_NUMBER = 0
        self.ERR_CRC = 1
        self.ERR_WROND_MID = 2
        self.ERR_PROTOCOL_CONTROL_WORD = 3
        self.ERR_CANT_EXECUTE_IN_CURR_STATUS = 4
        self.ERR_COMMAND_LIST_FULL = 5
        self.ERR_MESS_PARAMS_INCOMPLETE = 6
        self.ERR_FRAME_LEN_EXCEED_LIMIT = 7 # data len <= 1024 bytes
        self.ERR_OTHER = 8
        # Reader statuses
        self.STATUS_IDLE = 0
        self.STATUS_EXECUTION = 1
        self.STATUS_ERROR = 2
        # MIDs for TYPE_ERR_WARN
        self.ERR_MID = 0x00 # reader initiated frame only
        # MIDs for TYPE_CONF_MANAGE
        self.MAN_QUERY_INFO = 0x00
        self.MAN_QUERY_BASEBAND = 0x01
        self.MAN_CONF_RS232 = 0x02
        self.MAN_QUERY_RS232_CONF = 0x03
        self.MAN_IP_CONF = 0x04
        self.MAN_QUERY_IP = 0x05
        self.MAN_QUERY_MAC = 0x06
        self.MAN_CONF_CLI_SRV_MODE = 0x07
        self.MAN_QUERY_CLI_SRV_MODE = 0x08
        self.MAN_CONF_GPO = 0x09
        self.MAN_QUERY_GPI_STATUS = 0x0A
        self.MAN_CONF_GPI_TRIG = 0x0B
        self.MAN_QUERY_GPI_TRIG = 0x0C
        self.MAN_CONF_WIEGAND = 0x0D
        self.MAN_QUERY_WIEGAND = 0x0E
        self.MAN_RESTART = 0x0F
        self.MAN_CONF_TIME = 0x10
        self.MAN_QUERY_TIME = 0x11
        self.MAN_CONN_CONFIRM = 0x12
        self.MAN_CONF_MAC = 0x13
        self.MAN_RESTORE_DEFAULT = 0x14
        self.MAN_CONF_RS485_ADR = 0x15
        self.MAN_QUERY_RS485_ADR = 0x16
        self.MAN_TAG_DATA_RESPONSE = 0x1D
        self.MAN_BUZZ_CONTROL = 0x1F
        # Reply or initiated by reader
        self.MAN_READER_TRIG_START_MESS = 0x00 # reader initiated
        self.MAN_READER_TRIG_STOP_MESS = 0x01 # reader initiated
        self.MAN_READER_CONN_CONFIRM = 0x12 # reader initiated
        # MIDs for TYPE_CONF_OPERATE
        self.OP_QUERY_RFID_ABILITY = 0x00
        self.OP_CONF_POWER = 0x01
        self.OP_QUERY_POWER = 0x02
        self.OP_CONF_RF_BAND = 0x03
        self.OP_QUERY_RF_BAND = 0x04
        self.OP_CONF_FREQ = 0x05
        self.OP_QUERY_FREQ = 0x06
        self.OP_CONF_ANT = 0x07
        self.OP_QUERY_ANT = 0x08
        self.OP_CONF_TAG_UPLOAD = 0x09
        self.OP_QUERY_TAG_UPLOAD = 0x0A
        self.OP_CONF_EPC_BASEBAND = 0x0B
        self.OP_QUERY_EPC_BASEBAND = 0x0C
        self.OP_CONF_AUTO_IDLE = 0x0D
        self.OP_QUERY_AUTO_IDLE = 0xE
        self.OP_READ_EPC_TAG = 0x10
        self.OP_WRITE_EPC_TAG = 0x11
        self.OP_LOCK_TAG = 0x12
        self.OP_KILL_TAG = 0x13
        self.OP_READ_6B_TAG = 0x40
        self.OP_QRITE_6B_TAG = 0x41
        self.OP_LOCK_6B_TAG = 0x42
        self.OP_QUERY_6B_TAG_LOCKING = 0x43
        self.OP_STOP = 0xFF
        # Reply or initiated by reader
        self.OP_READER_EPC_DATA_UPLOAD = 0x00 # reader initiated
        self.OP_READER_EPC_READ_FINISH = 0x01 # reader initiated
        self.OP_READER_6B_DATA_UPLOAD = 0x02 # reader initiated
        self.OP_READER_6B_READ_QUIT = 0x03 # reader initiated
        self.DECODE_ERROR_TYPE = {
            0: "0 error type",
            1: "CRC calibration error",
            2: 'wrong MID',
            3: 'protocol control word other error',
            4: 'current status can not execute the command',
            5: 'command list full',
            6: 'message parameter incomplete',
            7: 'frame length exceed limitation',
            8: 'other error'
            }
        self.DECODE_READER_STATUS = {
            0: 'Idle status',
            1: 'Execution status',
            2: 'Error status'
            }
        self.FRAME_DIRECTION = ('SEND', 'RECEIVE')
        self.PARAM_HEADER_INIT = {
            'INIT_BY_READER': self.INIT_BY_READER,
            'INIT_BY_USER': self.INIT_BY_USER,
            'NULL': 0x00
            }
        self.DECODE_PARAM_HEADER_INIT = dict()
        __keys_tmp = str()
        for __keys_tmp in self.PARAM_HEADER_INIT.keys():
            if __keys_tmp != 'NULL':
                self.DECODE_PARAM_HEADER_INIT[(self.PARAM_HEADER_INIT[__keys_tmp])] = __keys_tmp
        self.PARAM_HEADER_RS485 = {
            'RS485_USED': self.RS485_USED,
            'RS485_NOT_USED': self.RS485_NOT_USED,
            'NULL': 0x00
            }
        self.DECODE_PARAM_HEADER_RS485 = dict()
        __keys_tmp = str()
        for __keys_tmp in self.PARAM_HEADER_RS485.keys():
            if __keys_tmp != 'NULL':
                self.DECODE_PARAM_HEADER_RS485[(self.PARAM_HEADER_RS485[__keys_tmp])] = __keys_tmp
        self.PARAM_HEADER_TYPE = {
            'TYPE_ERR_WARN': self.TYPE_ERR_WARN,
            'TYPE_CONF_MANAGE': self.TYPE_CONF_MANAGE,
            'TYPE_CONF_OPERATE': self.TYPE_CONF_OPERATE,
            'TYPE_LOG': self.TYPE_LOG,
            'TYPE_APP_UPGRADE': self.TYPE_APP_UPGRADE,
            'TYPE_TEST': self.TYPE_TEST,
            'NULL': 0x00
            }
        self.DECODE_PARAM_HEADER_TYPE = dict()
        __keys_tmp = str()
        for __keys_tmp in self.PARAM_HEADER_TYPE.keys():
            if __keys_tmp != 'NULL':
                self.DECODE_PARAM_HEADER_TYPE[(self.PARAM_HEADER_TYPE[__keys_tmp])] = __keys_tmp
        self.MID_ERR = {
            'ERR_MID': 0x00,
            'NULL': 0x00
            }
        self.DECODE_MID_ERR = {0x00: 'ERR_MID'}
        self.MID_MAN_USER_INIT = {
            'MAN_QUERY_INFO': 0x00,
            'MAN_QUERY_BASEBAND': 0x01,
            'MAN_CONF_RS232': 0x02,
            'MAN_QUERY_RS232_CONF': 0x03,
            'MAN_IP_CONF': 0x04,
            'MAN_QUERY_IP': 0x05,
            'MAN_QUERY_MAC': 0x06,
            'MAN_CONF_CLI_SRV_MODE': 0x07,
            'MAN_QUERY_CLI_SRV_MODE': 0x08,
            'MAN_CONF_GPO': 0x09,
            'MAN_QUERY_GPI_STATUS': 0x0A,
            'MAN_CONF_GPI_TRIG': 0x0B,
            'MAN_QUERY_GPI_TRIG': 0x0C,
            'MAN_CONF_WIEGAND': 0x0D,
            'MAN_QUERY_WIEGAND': 0x0E,
            'MAN_RESTART': 0x0F,
            'MAN_CONF_TIME': 0x10,
            'MAN_QUERY_TIME': 0x11,
            'MAN_CONN_CONFIRM': 0x12,
            'MAN_CONF_MAC': 0x13,
            'MAN_RESTORE_DEFAULT': 0x14,
            'MAN_CONF_RS485_ADR': 0x15,
            'MAN_QUERY_RS485_ADR': 0x16,
            'MAN_TAG_DATA_RESPONSE': 0x1D,
            'MAN_BUZZ_CONTROL': 0x1F,
            'NULL': 0x00
            }
        self.DECODE_MID_MAN_USER_INIT = dict()
        __keys_tmp = str()
        for __keys_tmp in self.MID_MAN_USER_INIT.keys():
            if __keys_tmp != 'NULL':
                self.DECODE_MID_MAN_USER_INIT[(self.MID_MAN_USER_INIT[__keys_tmp])] = __keys_tmp
        self.MID_MAN_READER_INIT = {
            'MAN_READER_TRIG_START_MESS': 0x00,
            'MAN_READER_TRIG_STOP_MESS': 0x01,
            'MAN_READER_CONN_CONFIRM': 0x12,
            'NULL': 0x00
            }
        self.DECODE_MID_MAN_READER_INIT = dict()
        __keys_tmp = str()
        for __keys_tmp in self.MID_MAN_READER_INIT.keys():
            if __keys_tmp != 'NULL':
                self.DECODE_MID_MAN_READER_INIT[(self.MID_MAN_READER_INIT[__keys_tmp])] = __keys_tmp
        self.MID_OP_USER_INIT = {
            'OP_QUERY_RFID_ABILITY': 0x00,
            'OP_CONF_POWER': 0x01,
            'OP_QUERY_POWER': 0x02,
            'OP_CONF_RF_BAND': 0x03,
            'OP_QUERY_RF_BAND': 0x04,
            'OP_CONF_FREQ': 0x05,
            'OP_QUERY_FREQ': 0x06,
            'OP_CONF_ANT': 0x07,
            'OP_QUERY_ANT': 0x08,
            'OP_CONF_TAG_UPLOAD': 0x09,
            'OP_QUERY_TAG_UPLOAD': 0x0A,
            'OP_CONF_EPC_BASEBAND': 0x0B,
            'OP_QUERY_EPC_BASEBAND': 0x0C,
            'OP_CONF_AUTO_IDLE': 0x0D,
            'OP_QUERY_AUTO_IDLE': 0xE,
            'OP_READ_EPC_TAG': 0x10,
            'OP_WRITE_EPC_TAG': 0x11,
            'OP_LOCK_TAG': 0x12,
            'OP_KILL_TAG': 0x13,
            'OP_READ_6B_TAG': 0x40,
            'OP_QRITE_6B_TAG': 0x41,
            'OP_LOCK_6B_TAG': 0x42,
            'OP_QUERY_6B_TAG_LOCKING': 0x43,
            'OP_STOP': 0xFF,
            'NULL': 0x00
            }
        self.DECODE_MID_OP_USER_INIT = dict()
        __keys_tmp = str()
        for __keys_tmp in self.MID_OP_USER_INIT.keys():
            if __keys_tmp != 'NULL':
                self.DECODE_MID_OP_USER_INIT[(self.MID_OP_USER_INIT[__keys_tmp])] = __keys_tmp
        self.MID_OP_READER_INIT = {
            'OP_READER_EPC_DATA_UPLOAD': 0x00,
            'OP_READER_EPC_READ_FINISH': 0x01,
            'OP_READER_6B_DATA_UPLOAD': 0x02,
            'OP_READER_6B_READ_QUIT': 0x03,
            'NULL': 0x00
            }
        self.DECODE_MID_OP_READER_INIT = dict()
        __keys_tmp = str()
        for __keys_tmp in self.MID_OP_READER_INIT.keys():
            if __keys_tmp != 'NULL':
                self.DECODE_MID_OP_READER_INIT[(self.MID_OP_READER_INIT[__keys_tmp])] = __keys_tmp
        self.MID = [[{'NULL': 0x00}, self.MID_ERR], [self.MID_MAN_USER_INIT, self.MID_MAN_READER_INIT], [self.MID_OP_USER_INIT, self.MID_OP_READER_INIT]]
        self.DECODE_MID = [[{0x00: 'NULL'}, self.DECODE_MID_ERR], [self.DECODE_MID_MAN_USER_INIT, self.DECODE_MID_MAN_READER_INIT], [self.DECODE_MID_OP_USER_INIT, self.DECODE_MID_OP_READER_INIT]]
        self.FULL_MID_LIST = list(self.MID_MAN_USER_INIT.keys())
        self.FULL_MID_LIST += list(self.MID_MAN_READER_INIT.keys())
        self.FULL_MID_LIST += list(self.MID_OP_USER_INIT.keys())
        self.FULL_MID_LIST += list(self.MID_OP_READER_INIT.keys())
        self.FULL_MID_LIST += list(self.MID_ERR.keys())
        self.DECODE_FRAME_ERRORS = {
            0: 'OK',
            1: 'No 0xAA frame header symbol',
            2: 'CRC error',
            3: 'Frame len < minimum required bytes',
            4: 'Message type > 5',
            5: 'Reserved bits in control word are not 0',
            6: 'Wrong MID number for control word',
            7: 'RS485 not supported',
            8: 'Frame data len parameter not match frame data len'
            }
        self.DECODE_TAG_DATA = {    # Attention! Also a pivate copy defined in class TagData()
            0x01: 'RSSI', # RSSI
            0x02: 'DATA_READ_RESULT', # tag data read result
            0x03: 'TID', # Tag TID data
            0x04: 'USER_AREA', # Tag user area data
            0x05: 'RETENTION_AREA', # tag retention area data
            0x06: 'SUB_ANT', # Sub antenna number, 1-16
            0x07: 'TIME', # Tag reading time UTC
            0x08: 'SERIES_NUM', # Tag response package series number
            0x09: 'FREQ', # Current frequency
            0x0A: 'PHASE', # Current tag phase
            0x0B: 'EM_SENSOR_DATA', # EM SensorData
            0x0C: 'ADDITIONAL_DATA'  # Tag EPC data
            }
        self.TAG_DATA = dict()
        __keys_tmp = str()
        for __keys_tmp in self.DECODE_TAG_DATA.keys():
            self.TAG_DATA[(self.DECODE_TAG_DATA[__keys_tmp])] = __keys_tmp
        self.DECODE_TAG_DATA_READ_RESULT = { # Attention! Also a pivate copy defined in class TagData()
            0: "Read successful",
            1: "Tag no response",
            2: "CRC error",
            3: "Data area is locked",
            4: "Data area overflow",
            5: "Access password error",
            6: "Other tag error",
            7: "Other reader error"
        }
        self.FREQ_BANDS = {
            0: '920~925MHz',
            1: '840~845MHz',
            2: '840~845MHz & 920~925MHz',
            3: 'FCC: 902~928MHz',
            4: 'ETSI: 866~868MHz',
            5: 'JP: 916.8~920.4MHz',
            6: 'TW: 922.25~927.75MHz',
            7: 'ID: 923.125~925.125MHz',
            8: 'RU: 866.6~867.4MHz'
            }
        self.RFID_PROTOCOLS = {
            0: 'ISO18000-6C/EPC C1G2',
            1: 'ISO18000-6B',
            2: 'China standard GB/T 29768-2013',
            3: 'China Military GJB 7383.1-2011'
            }
        self.DECODE_READ_EPC_TAG = {
            0: 'Configure successfully',
            1: 'Antenna port parameter error',
            2: 'Select read parameter error',
            3: 'TID read parameter error',
            4: 'User data area read parameter error',
            5: 'Retention area read parameter error',
            6: 'Other parameter error'
            }
        self.FREQ_AUTO_SETTING = {
            0: 'MANUAL',
            1: 'AUTO'
            }

class Crc16Ibm:
    """ Calculating CRC16 IBM non-reversed """
    def __init__(self):
        """ Initializing lookup table """
        self.__pol = 0x8005
        self.__crc_table = list()
        for __i in range(256):
            __rg = __i << 8
            for __j in range(8):
                if (__rg >> 15) == 1:
                    __rg = ((__rg << 1) ^ self.__pol) & 0xFFFF
                else:
                    __rg = __rg << 1
            self.__crc_table.append(__rg)
    def crc16sum(self, in_data):
        """ Calculating CRC32 IBM from in_data, expected bytes() """
        __crc16reg = 0x0000
        if not isinstance(in_data, bytes):
            return -1
        for __idx in range(len(in_data)):
            __new_byte = in_data[__idx]
            __rgout = __crc16reg >> 8
            __crc16reg = ((__crc16reg << 8) & 0xFFFF)
            __crc16reg = self.__crc_table[__rgout ^ __new_byte] ^ __crc16reg
        return __crc16reg

class TagData:
    """ Data structure for RFID tag data received from Clou scanner """
    def __init__(self, rs485_mark_set=0):
        """
        If the reader is connected via RS485, please set rs485_mark_set=1
        when initializing the class instance!
        """
        assert isinstance(rs485_mark_set, int), "rs485_mark_set must be int()"
        assert (rs485_mark_set == 0) or (rs485_mark_set == 1), "rs485_mark_set value must be 0 or 1"
        self.EPC_code = bytes()
        self.PC_value = 0
        self.ant_id = 0
        self.params = dict()    # dictionary for decoding optional parameters DECODE_TAG_DATA[]
        self.decode_error = False
        self.decode_error_text = str()
        self.EPC_len = 0
        self.UMI = 0
        self.XPC_indicator = 0
        self.num_sys_id_toggle = 0
        self.RFU = 0
        self.__rs485_mark = rs485_mark_set  # rs485_mark value the same as for ClouRFIDFrame() class init
        self.__DECODE_TAG_DATA = {
            0x01: 'RSSI', # RSSI
            0x02: 'DATA_READ_RESULT', # tag data read result
            0x03: 'TID', # Tag TID data
            0x04: 'USER_AREA', # Tag user area data
            0x05: 'RETENTION_AREA', # tag retention area data
            0x06: 'SUB_ANT', # Sub antenna number, 1-16
            0x07: 'TIME', # Tag reading time UTC
            0x08: 'SERIES_NUM', # Tag response package series number
            0x09: 'FREQ', # Current frequency
            0x0A: 'PHASE', # Current tag phase
            0x0B: 'EM_SENSOR_DATA', # EM SensorData
            0x0C: 'ADDITIONAL_DATA'  # Tag EPC data
            }
        self.__DECODE_TAG_DATA_READ_RESULT = {
            0: "Read successful",
            1: "Tag no response",
            2: "CRC error",
            3: "Data area is locked",
            4: "Data area overflow",
            5: "Access password error",
            6: "Other tag error",
            7: "Other reader error"
        }
    def encodeInDict(self):
        """
        Method to encode instance properties into dict()
        """
        res_dict = dict()
        res_i = int()
        res_dict["EPC_code"] = str()
        for res_i in range(len(self.EPC_code)):
            res_dict["EPC_code"] += "{0:02X}".format(self.EPC_code[res_i])
        res_dict["ant_id"] = self.ant_id
        res_dict["params"] = dict()
        for tmp_dict_keys in self.params.keys():
            if tmp_dict_keys == 0x02:
                res_dict["params"][self.__DECODE_TAG_DATA[tmp_dict_keys]] = self.__DECODE_TAG_DATA_READ_RESULT[self.params[tmp_dict_keys]]
            elif tmp_dict_keys in [0x03, 0x04, 0x05, 0x08, 0x0C]:
                res_i = int()
                res_dict["params"][self.__DECODE_TAG_DATA[tmp_dict_keys]] = str()
                for res_i in range(len(self.params[tmp_dict_keys])):
                    res_dict["params"][self.__DECODE_TAG_DATA[tmp_dict_keys]] += "{0:02X}".format(self.params[tmp_dict_keys][res_i])
            else:
                res_dict["params"][self.__DECODE_TAG_DATA[tmp_dict_keys]] = self.params[tmp_dict_keys]
        res_dict["decode_error"] = self.decode_error
        res_dict["EPC_len"] = self.EPC_len * 16
        res_dict["UMI"] = self.UMI
        res_dict["XPC_indicator"] = self.XPC_indicator
        res_dict["num_sys_id_toggle"] = self.num_sys_id_toggle
        res_dict["RFU"] = "0x" + "{0:02X}".format(self.RFU)
        return res_dict
    def decodeTag(self, received_frame_bytes):
        """
        Decode tag data frame in raw bytes()
        received_frame_bytes - bytes() received from Clou scanner - output of ClouRFIDFrame().decodeFrame()
        """
        # First clean properties to defaults:
        self.EPC_code = bytes()
        self.PC_value = 0
        self.ant_id = 0
        self.params = dict()
        self.decode_error = False
        self.decode_error_text = str()
        self.EPC_len = 0
        self.UMI = 0
        self.XPC_indicator = 0
        self.num_sys_id_toggle = 0
        self.RFU = 0
        if not isinstance(received_frame_bytes, bytes):
            self.decode_error = True
            self.decode_error_text = "Error: received_frame_bytes in decodeTag() is not bytes()"
            return
        try:
            response_frame_data = received_frame_bytes  # [(3 + self.__rs485_mark):-2] - optional but not needed - cut the header from the frame and the CRC in the end of frame
            line_index = 2              # start of line index - at 3rd byte just after frame data len
            tmp_epc_len = (256 * response_frame_data[line_index]) + response_frame_data[line_index+1]
            line_index += 2             # shift index to EPC code content
            self.EPC_code += response_frame_data[line_index:(line_index+tmp_epc_len)]
            line_index += tmp_epc_len   # shift index to next parameter = tag PC value
            del tmp_epc_len
            self.PC_value = (256 * response_frame_data[line_index]) + response_frame_data[line_index+1]
            tmp_PC_val = response_frame_data[line_index]
            (tmp_PC_val, self.num_sys_id_toggle) = divmod(tmp_PC_val, 2**1)
            (tmp_PC_val, self.XPC_indicator) = divmod(tmp_PC_val, 2**1)
            (tmp_PC_val, self.UMI) = divmod(tmp_PC_val, 2**1)
            (tmp_PC_val, self.EPC_len) = divmod(tmp_PC_val, 2**5)
            del tmp_PC_val
            self.RFU = response_frame_data[line_index+1]
            line_index += 2             # shift index to antenna ID
            self.ant_id = response_frame_data[line_index]
            line_index += 1             # shift to optional params block
            tmp_exit_flag = False
            while not tmp_exit_flag:
                if line_index == len(response_frame_data):
                    tmp_exit_flag = True
                elif line_index < len(response_frame_data):
                    tmp_opt_param = response_frame_data[line_index]
                    if tmp_opt_param == 0x01:      # ============= RSSI
                        line_index += 1     # shift index to optional parameter contents (starting from 2 byte len if variable len param)
                        self.params[tmp_opt_param] = response_frame_data[line_index]
                        line_index += 1     # shift index forward to next opt param id
                    elif tmp_opt_param == 0x02:    # ============= read result
                        line_index += 1
                        self.params[tmp_opt_param] = response_frame_data[line_index]
                        line_index += 1
                    elif (tmp_opt_param == 0x03) or (tmp_opt_param == 0x04) or (tmp_opt_param == 0x05) or (tmp_opt_param == 0x0C):
                        line_index += 1
                        tmp_opt_p_len = (256 * response_frame_data[line_index]) + response_frame_data[line_index+1]
                        line_index += 2
                        self.params[tmp_opt_param] = bytes()
                        self.params[tmp_opt_param] += response_frame_data[line_index:(line_index+tmp_opt_p_len)]
                        line_index += tmp_opt_p_len
                        del tmp_opt_p_len
                    elif tmp_opt_param == 0x06:
                        pass
                    elif tmp_opt_param == 0x07:
                        line_index += 1
                        tmp_sec = float()
                        tmp_sec += (256**3) * response_frame_data[line_index+0]
                        tmp_sec += (256**2) * response_frame_data[line_index+1]
                        tmp_sec += (256**1) * response_frame_data[line_index+2]
                        tmp_sec += (256**0) * response_frame_data[line_index+3]
                        tmp_microsec = float()
                        tmp_microsec += (256**3) * response_frame_data[line_index+4]
                        tmp_microsec += (256**2) * response_frame_data[line_index+5]
                        tmp_microsec += (256**1) * response_frame_data[line_index+6]
                        tmp_microsec += (256**0) * response_frame_data[line_index+7]
                        self.params[tmp_opt_param] = tmp_sec + (tmp_microsec / 1000000)
                        line_index += 8
                        del tmp_microsec, tmp_sec
                    elif tmp_opt_param == 0x08:
                        line_index += 1
                        self.params[tmp_opt_param] = bytes()
                        self.params[tmp_opt_param] += response_frame_data[line_index:(line_index+4)]
                        line_index += 4
                    elif tmp_opt_param == 0x09:
                        pass
                    elif tmp_opt_param == 0x0A:
                        pass
                    elif tmp_opt_param == 0x0B:
                        pass
                else:
                    self.decode_error_text = "Error: wrong optional params detected in decodeTag()"
                    self.decode_error = True
                    return
            del tmp_exit_flag, line_index
        except Exception:
            self.decode_error = True
            self.decode_error_text = "Error: error decoding in try: except: block"
            return

class ClouRFIDFrame(ClouProtocolDefinitions, Crc16Ibm):        # Clou RFID reader frame description
    """ Class realizing encoding and decoding frames to communicate with Clou reader """
    frame_head = 0xAA # frame head, constant
    def __init__(self, message_id_set=0, message_type_set=0, init_by_reader_set=0, rs485_mark_set=0, rs485_id_set=0, data_bytes_transmit=bytes()):
        """
        Initialize instance with parameters for encoding for sending,
        for decoding can be initialized with empty parameters ClouRFIDFrame()
        """
        ClouProtocolDefinitions.__init__(self)
        Crc16Ibm.__init__(self)
        self.message_id = message_id_set # MID number = 7-0 message ID 0x00~0xFF (MID) differentiate detailed message below same type message
        self.message_type = message_type_set # 11-8 message type number, 0x5~0xF, reserved
        self.init_by_reader = init_by_reader_set # 12 = 0 means message is PC command or reader response to PC command, 1 means reader initiated
        self.rs485_mark = rs485_mark_set # 13 1 means this message is used for RS485 communication, 0 - otherwise
        self.rs485_id = rs485_id_set # ID of reader on RS-485 bus
        self.data_bytes = data_bytes_transmit # data bytes() to transmit in encodeFrame() and received in decodeFrame()
        self.frame_raw_line = bytes()
        self.start_data_with_len = True
    reserved_bits = 0x00 # 15-14 Reserved bit = keep 0
    def encodeFrame(self):
        """ Encoding basing on parameters in properties, result is in self.frame_raw_line """
        self.frame_raw_line = bytes()
        result_data = bytes()
        result_data += bytes([self.frame_head])
        result_data += bytes([self.message_type + (self.init_by_reader << 4) + (self.rs485_mark << 5)])
        result_data += bytes([self.message_id])
        if self.rs485_mark == self.RS485_USED:
            result_data += bytes([self.rs485_id])
        len_msb = len(self.data_bytes) // 256
        len_lsb = len(self.data_bytes) % 256
        if self.start_data_with_len:
            result_data += bytes([len_msb])
            result_data += bytes([len_lsb])
        result_data += self.data_bytes
        crc16_value = self.crc16sum(result_data[1:])
        crc16_msb = crc16_value // 256
        crc16_lsb = crc16_value % 256
        result_data += bytes([crc16_msb])
        result_data += bytes([crc16_lsb])
        self.frame_raw_line = result_data
        del len_msb, len_lsb, crc16_value, crc16_msb, crc16_lsb
        return 0
    def decodeFrame(self):
        """
        Decoding, first put the bytes() line from scanner to
        self.frame_raw_line, then call decodeFrame(),
        as result properties of the instance will be
        filled with decoded data.
        """
        self.message_id = int()
        self.message_type = int()
        self.init_by_reader = int()
        self.rs485_mark = int()
        self.rs485_id = int()
        self.data_bytes = bytes()
        if len(self.frame_raw_line) < 7:
            return 3
        if self.frame_raw_line[0] != 0xAA:
            return 1
        crc16_value = self.crc16sum(self.frame_raw_line[1:-2])
        crc16_msb = crc16_value // 256
        crc16_lsb = crc16_value % 256
        if ((crc16_msb != self.frame_raw_line[-2]) or (crc16_lsb != self.frame_raw_line[-1])):
            del crc16_value, crc16_msb, crc16_lsb
            return 2
        control_symb_tmp = self.frame_raw_line[1]
        message_type_tmp = control_symb_tmp % (2**4)
        if message_type_tmp > 5:
            del crc16_value, crc16_msb, crc16_lsb, control_symb_tmp, message_type_tmp
            return 4
        init_by_reader_tmp = (control_symb_tmp // (2**4)) % 2
        rs485_mark_tmp = (control_symb_tmp // (2**5)) % 2
        rs485_added_1 = 0
        if rs485_mark_tmp == self.RS485_USED:
            self.rs485_id = self.frame_raw_line[3]
            rs485_added_1 = 1
        if (control_symb_tmp // (2**6)) != 0:
            del crc16_value, crc16_msb, crc16_lsb, control_symb_tmp, message_type_tmp, init_by_reader_tmp, rs485_mark_tmp, rs485_added_1
            return 5
        self.message_id = self.frame_raw_line[2]
        self.data_bytes = self.frame_raw_line[(3 + rs485_added_1):-2]
        if (len(self.data_bytes) - 2) != ((256 * self.data_bytes[0]) + self.data_bytes[1]):
            del crc16_value, crc16_msb, crc16_lsb, control_symb_tmp, message_type_tmp, init_by_reader_tmp, rs485_mark_tmp, rs485_added_1
            return 8
        self.message_type = message_type_tmp
        self.init_by_reader = init_by_reader_tmp
        self.rs485_mark = rs485_mark_tmp
        self.frame_raw_line = bytes()
        del crc16_value, crc16_msb, crc16_lsb, control_symb_tmp, message_type_tmp, init_by_reader_tmp, rs485_mark_tmp, rs485_added_1
        return 0
    def decodeCtrlWord(self):
        """
        Decoding only frame control word, first put only 2 bytes of "control word"
        to self.frame_raw_line, then call decodeCtrlWord(),
        as result all properties of the instance except data_bytes will be
        filled with decoded data.
        The method developed with almost zero error handling,
        in case of error returns -1.
        """
        self.message_id = int()
        self.message_type = int()
        self.init_by_reader = int()
        self.rs485_mark = int()
        self.rs485_id = int()
        self.data_bytes = bytes()
        if len(self.frame_raw_line) != 2:
            return -1
        control_symb_tmp = self.frame_raw_line[0]
        message_type_tmp = control_symb_tmp % (2**4)
        if message_type_tmp > 5:
            del control_symb_tmp, message_type_tmp
            return -1
        init_by_reader_tmp = (control_symb_tmp // (2**4)) % 2
        rs485_mark_tmp = (control_symb_tmp // (2**5)) % 2
        if (control_symb_tmp // (2**6)) != 0:
            del control_symb_tmp, message_type_tmp, init_by_reader_tmp, rs485_mark_tmp
            return -1
        self.message_id = self.frame_raw_line[1]
        self.message_type = message_type_tmp
        self.init_by_reader = init_by_reader_tmp
        self.rs485_mark = rs485_mark_tmp
        self.frame_raw_line = bytes()
        del control_symb_tmp, message_type_tmp, init_by_reader_tmp, rs485_mark_tmp
        return 0
    def clear(self):
        """
        Clear to emtpy state, same as after init
        """
        self.message_id = int()
        self.message_type = int()
        self.init_by_reader = int()
        self.rs485_mark = int()
        self.rs485_id = int()
        self.data_bytes = bytes()
        self.frame_raw_line = bytes()
        self.start_data_with_len = True

class ClouLogging(ClouRFIDFrame, TagData):
    """ Main and the only class in the module """
    def __init__(self, log_dir_path_set, logfile_head_str_set, timezone_set="+0000", log_stdout_set=False):
        """
        log_dir_path_set - dir to put logfiles
        logfile_head_str_set - header string for log file name
        timezone_set - 5 symbol str() in format '+HHMM' or '-HHMM' meaning timezone shift
        log_stdout_set - bool(), if True then duplicate logging on standard output
        """
        ClouRFIDFrame.__init__(self)
        TagData.__init__(self)
        assert isinstance(log_dir_path_set, str), "log_dir_path_set must be str()"
        assert log_dir_path_set != str(), "log_dir_path_set length must be > 0"
        assert os_access("/" + log_dir_path_set.strip("/"), os_F_OK), log_dir_path_set + " does not exist"
        assert isinstance(logfile_head_str_set, str), "logfile_head_str_set must be str()"
        assert logfile_head_str_set != str(), "logfile_head_str_set length must be > 0"
        assert isinstance(timezone_set, str), "timezone_set must be str()"
        assert len(timezone_set) == 5, "timezone_set must be 5 symbols length"
        assert (timezone_set[0] == "-") or (timezone_set[0] == "+"), "timezone_set must start from - or +"
        assert isinstance(log_stdout_set, bool), "log_stdout_set must be bool()"
        self.__log_dir_path = "/" + log_dir_path_set.strip("/")
        self.__logfile_head = logfile_head_str_set
        self.__timezone_str = timezone_set
        __tz = float()
        try:
            __tzh = int(timezone_set[1:3])
            __tzm = int(timezone_set[3:5])
            if timezone_set[0] == "-":
                __tz = (-1.00) * (float(__tzh) + float(__tzm / 60))
            else:
                __tz = (+1.00) * (float(__tzh) + float(__tzm / 60))
        except Exception:
            __tz = float()
        self.__timezone = float(__tz)
        self.__log_stdout = log_stdout_set
    def log(self, message_text, instance_to_log=0, result_resp=0, explicit_timestamp=None, put_timestamp=True):
        """
        Method to log the message and detailed data
        message_text - str() text message to put to log
        instance_to_log - must be either ClouRFIDFrame() or TagData() instance
        result_resp - can put here int() return result from ClouRFIDFrame().decodeFrame()
        put_timestamp - bool() set False if no need to put timestamp in each line inside log file
        """
        assert (explicit_timestamp is None) or isinstance(explicit_timestamp, float), "explicit_timestamp must be float() or None"
        log_text_out = list()
        s_tmp = str()
        if explicit_timestamp is None:
            time_stamp_to_log = time() + (self.__timezone * 3600)
        else:
            time_stamp_to_log = explicit_timestamp + (self.__timezone * 3600)
        gmtime_stamp_to_log = gmtime(time_stamp_to_log)
        if put_timestamp:
            s_tmp = strftime("[ %d.%m.%Y %H:%M:%S." + str(time_stamp_to_log - int(time_stamp_to_log))[2:8] + self.__timezone_str + " ] > ", gmtime_stamp_to_log) + str(message_text)
        else:
            s_tmp = str(message_text)
        if isinstance(instance_to_log, ClouRFIDFrame):
            s_tmp = s_tmp + " [ " + self.DECODE_FRAME_ERRORS[result_resp] + " ] "
            s_tmp = s_tmp + "[ " + self.DECODE_MID[instance_to_log.message_type][instance_to_log.init_by_reader][instance_to_log.message_id] + " ] "
            s_tmp = s_tmp + "[ " + self.DECODE_PARAM_HEADER_INIT[instance_to_log.init_by_reader] + " ] "
            s_tmp = s_tmp + "[ " + self.DECODE_PARAM_HEADER_RS485[instance_to_log.rs485_mark] + " ] "
            s_tmp = s_tmp + "[ " + self.DECODE_PARAM_HEADER_TYPE[instance_to_log.message_type] + " ] "
            s_tmp = s_tmp + "[ DATA LEN = " + "{0:02X}".format(len(instance_to_log.data_bytes)) + " ]"
            s_tmp = s_tmp + " [ "
            j = 0
            for j in range(len(instance_to_log.data_bytes)):
                s_tmp = s_tmp + "{0:02X}".format(instance_to_log.data_bytes[j]) + " "
            s_tmp = s_tmp + "]"
        if s_tmp:
            log_text_out.append(s_tmp)
        if isinstance(instance_to_log, TagData):
            log_text_out.append("Tag EPC code       = " + str().join(format(idx_hex_conv, '02X') for idx_hex_conv in instance_to_log.EPC_code))
            log_text_out.append("Tag EPC len        = " + str(instance_to_log.EPC_len * 16) + " bits")
            log_text_out.append("Tag UMI            = " + str(instance_to_log.UMI))
            log_text_out.append("Tag XPC indicator  = " + str(instance_to_log.XPC_indicator))
            log_text_out.append("Tag num system id  = " + str(instance_to_log.num_sys_id_toggle))
            log_text_out.append("Tag RFU            = 0x" + "{0:02X}".format(instance_to_log.RFU))
            log_text_out.append("Antenna ID         = " + str(instance_to_log.ant_id))
            for op_keys in instance_to_log.params.keys():
                if op_keys == self.TAG_DATA['RSSI']:
                    log_text_out.append("RSSI value         = " + str(instance_to_log.params[op_keys]))
                elif op_keys == self.TAG_DATA['DATA_READ_RESULT']:
                    log_text_out.append("Read result        = " + str(instance_to_log.params[op_keys]))
                elif op_keys == self.TAG_DATA['TIME']:  # In timezone set in Clou scanner settings
                    log_text_out.append("Time when scanned  = " + strftime("%d.%m.%Y %H:%M:%S", gmtime(instance_to_log.params[op_keys])))
                elif op_keys == self.TAG_DATA['SERIES_NUM']:
                    log_text_out.append("Frame serial num   = " + str().join(format(idx_hex_conv, '02X') for idx_hex_conv in instance_to_log.params[0x08]))
        log_file = open(self.__log_dir_path + "/" + self.__logfile_head + strftime("-%Y-%m-%d-%H" + self.__timezone_str + ".log", gmtime_stamp_to_log), "a")
        del time_stamp_to_log, gmtime_stamp_to_log
        for j in range(len(log_text_out)):
            if self.__log_stdout:
                print(log_text_out[j])
            log_file.write(log_text_out[j].replace("\r", str()) + "\n")
        log_file.close()
        del j, log_text_out

class SessionState:
    """
    Structure containing status properties used in main loop of cloucon.py
    self.connected - False means not connected, True means now connected
    """
    def __init__(self):
        self.connected = False  # False means now not connected, True means now connected
        self.global_shutdown_flag = False   # Launch app with False shutdown flag

class ReceivedRawLine(Crc16Ibm):
    """
    Class handling the raw datastream coming from reader.
    It gets chunks of data received from socket, concatenates,
    and make the split of the whole stream into frames,
    which are stored in the list of bytes().
    """
    def __init__(self, parse_limit_set, rs485_mark_set=0):
        """
        parse_limit_set sets int() to limit max quantity of frames
        to parse in one call of unpack(), to limit the time spent,
        as new and new frames coming it can be helpful to respond and
        return to parsing later on.
        If your reader is connected with RS485, then please
        set rs485_mark_set=1, and in this case you can not mix unpacking
        for RS485 raw received input and TCP/IP raw input in one
        same instance of ReceivedRawLine() - so please create separate
        instances of the class in your code!
        """
        assert isinstance(parse_limit_set, int), "parse_limit_set must be int()"
        assert isinstance(rs485_mark_set, int), "rs485_mark_set must be int()"
        assert (rs485_mark_set == 0) or (rs485_mark_set == 1), "rs485_mark_set value must be 0 or 1"
        Crc16Ibm.__init__(self)
        self.frames = list()            # Public, main storage for frames bytes extracted from incoming stream
        self.__raw_stream = bytes()     # Main storage unit for raw bytes received from reader
        self.__err_text = str()         # Error explaining text
        self.__rs485_mark = rs485_mark_set  # rs485_mark value the same as for ClouRFIDFrame() class init
        self.__parse_limit = parse_limit_set
        self.__unknown_bytes = list()   # List of bytes() objects, in each - unknown bytes left after unpack() calls
    def add_to_stream(self, new_chunk_of_bytes):
        """
        Method to add new piece of bytes() received from socket
        new_chunk_of_bytes - bytes()
        Return -1 if error, and 0 if OK success.
        Error explanation text you can get using geterr() method of the class.
        """
        self.__err_text = str()
        if not isinstance(new_chunk_of_bytes, bytes):
            self.__err_text = "new_chunk_of_bytes in ReceivedRawLine() add() method must be bytes()"
            return -1
        self.__raw_stream += new_chunk_of_bytes # Important - here appending the chunk to the end of raw stream
        return 0
    def clear_stream(self):
        """ Method to erase contents of the raw bytes stream """
        self.__err_text = str()
        self.__raw_stream = bytes()
    def get_unknowns(self):
        """ Get unknown bytes in a list() of bytes() objects, after returning it clears unknowns """
        self.__err_text = str()
        __to_return = self.__unknown_bytes
        self.__unknown_bytes = list()
        return __to_return
    def geterr(self):
        """
        Method to get error textual explanation if returned -1 from
        a method of the class, geterr() output is str().
        """
        return self.__err_text
    def unpack(self):
        """
        Main method of the class, just unpacks the data stream
        stored in the class instance at the moment of call.
        The idea is first to get new chunk from socket,
        then append it to the instance storage with add_to_stream(),
        and finally call this unpack() method.
        It extracts correct frames from the stream, and puts them
        in frames storage list() named 'frames', the public property of the class.
        Returns 0 if success, -1 if error, error explanation take from geterr() method.
        """
        self.__err_text = str()
        try:
            parsing_exit_flag = True
            parsing_exit_counter = 0
            while (len(self.__raw_stream) >= (7 + self.__rs485_mark)) and parsing_exit_flag:
                parsing_exit_counter += 1
                if parsing_exit_counter >= self.__parse_limit:
                    parsing_exit_flag = False
                tmp_idx = 0 # if there are more than one 0xAA in a response_raw_line_stream?
                tmp_idx_break_flag = True
                while tmp_idx_break_flag:
                    response_raw_line_AA_idx = self.__raw_stream.find(0xAA, tmp_idx)
                    # here check whether there are possibility to have correct packet from reader in a string
                    # this below is only if there is a good chance to have
                    # the correct message fully collected from TCP
                    if (response_raw_line_AA_idx > -1) and ((len(self.__raw_stream) - response_raw_line_AA_idx) >= (7 + self.__rs485_mark)):
                        tmp_idx = response_raw_line_AA_idx + 1
                        res_cut_line_tmp = bytes()
                        res_cut_line_tmp += self.__raw_stream[response_raw_line_AA_idx:(response_raw_line_AA_idx + 5 + self.__rs485_mark)]
                        len_tmp = (256 * self.__raw_stream[3 + response_raw_line_AA_idx + self.__rs485_mark]) + self.__raw_stream[4 + response_raw_line_AA_idx + self.__rs485_mark]
                        if (len_tmp <= 4096) and ((len(self.__raw_stream) - response_raw_line_AA_idx) >= (7 + len_tmp + self.__rs485_mark)):
                            res_cut_line_tmp += self.__raw_stream[(5 + self.__rs485_mark + response_raw_line_AA_idx):(5 + self.__rs485_mark + len_tmp + 2 + response_raw_line_AA_idx)]
                            res_cut_line_tmp_crc = res_cut_line_tmp[1:-2]
                            crc16_u_value = self.crc16sum(res_cut_line_tmp_crc)
                            crc16_u_msb = crc16_u_value // 256
                            crc16_u_lsb = crc16_u_value % 256
                            if (crc16_u_msb == res_cut_line_tmp[-2]) and (crc16_u_lsb == res_cut_line_tmp[-1]):
                                self.frames.append(res_cut_line_tmp)    # Here append the decoded frame to the frames list!
                                new_raw_line = bytes()
                                new_raw_line = self.__raw_stream[(len(res_cut_line_tmp) + response_raw_line_AA_idx):]
                                if response_raw_line_AA_idx > 0:
                                    self.__unknown_bytes.append(self.__raw_stream[:response_raw_line_AA_idx])
                                self.__raw_stream = bytes()
                                self.__raw_stream = new_raw_line
                                tmp_idx_break_flag = False
                                del new_raw_line
                            del crc16_u_msb, crc16_u_lsb, crc16_u_value, res_cut_line_tmp_crc
                        del res_cut_line_tmp, len_tmp
                    else:
                        tmp_idx_break_flag = False
                    del response_raw_line_AA_idx
                del tmp_idx, tmp_idx_break_flag
            del parsing_exit_counter, parsing_exit_flag
        except Exception:
            self.__err_text = "Error unpacking in try: except: block"
            return -1
        return 0

class PackDataToClou(ClouProtocolDefinitions):
    """
    Class delivering Clou protocol specifics to
    pack and unpack data bytes from Clou frames
    from and to JSON files, describing the Clou
    protocol command & response
    """
    def __init__(self, cloutemplates_dir_set):
        """
        Initialize properties,
        cloutemplates_dir_set - directory name where to look for commands templates JSON files
        """
        assert isinstance(cloutemplates_dir_set, str), "cloutemplates_dir_set must be str()"
        ClouProtocolDefinitions.__init__(self)
        self.__cloutemplates_dir = "/" + cloutemplates_dir_set.strip("/")
        self.__cmd_template_dict = dict()
        self.decode_error = False
        self.decode_error_text = str()
    def packFromSndDict(self, snd_dict):
        """
        Pack the data to data_bytes parameter for ClouRFIDFrame(),
        snd_dict - dict() from JSON of the command representing
        the top "snd" key of the command template JSON.
        Output is a bytes() representing the data to pass to ClouRFIDFrame().encodeFrame()
        """
        self.decode_error = False
        self.decode_error_text = str()
        __data_bytes_out = bytes()
        __progress_mark = int()
        # Loading *.json file with the requested MID in snd_dict["msid"]
        try:
            __cloutemplates_file = open(self.__cloutemplates_dir + "/" + snd_dict["msid"] + ".json", "r")
        except Exception:
            self.decode_error = True
            self.decode_error_text = "Can not open file " + self.__cloutemplates_dir + "/" + snd_dict["msid"] + ".json for reading"
            return bytes()
        try:
            __tdict = load(__cloutemplates_file, encoding="utf-8")
        except Exception:
            self.decode_error = True
            self.decode_error_text = "Wrong JSON in file " + self.__cloutemplates_dir + "/" + snd_dict["msid"] + ".json"
            return bytes()
        # Close the file
        __progress_mark = 1
        __cloutemplates_file.close()
        try:
            # Looking for all entries of '[]' template in "tmpl" key of the "snd" JSON
            __data_template_found = re_findall("\[(\S+?)\]", __tdict["snd"]["tmpl"])
        except Exception:
            self.decode_error = True
            self.decode_error_text = "Error parsing template ['snd']['tmpl']"
            return bytes()
        # Here global try: wrapping the code block bery sensitive to human factor mistakes in content
        try:
            # Checks of __data_template_found
            __progress_mark = 2
            if not isinstance(__data_template_found, list):
                self.decode_error = True
                self.decode_error_text = "re.findall() for ['snd']['tmpl'] must return list()"
                return bytes()
            __progress_mark = 3
            for __tmp_idx_list0 in __data_template_found:
                __progress_mark = 4
                if not isinstance(__tmp_idx_list0, str):
                    self.decode_error = True
                    self.decode_error_text = "template keys in [] must be parsed as str()"
                    return bytes()
                __progress_mark = 5
                if ("[" in __tmp_idx_list0) or ("]" in __tmp_idx_list0):
                    self.decode_error = True
                    self.decode_error_text = "template keys names in [] must not contain [ or ] symbols"
                    return bytes()
                __progress_mark = 6
                if not __tmp_idx_list0.isascii():
                    self.decode_error = True
                    self.decode_error_text = "template keys must contain be only ASCII characters"
                    return bytes()
                __progress_mark = 7
                if __tmp_idx_list0 not in snd_dict["prms"].keys():
                    __progress_mark = 701
                    if __tdict["snd"]["prms"][__tmp_idx_list0]["pid"] == "M":
                        self.decode_error = True
                        self.decode_error_text = "mandatory template key '" + __tmp_idx_list0 + "' not in snd_dict['prms'] keys"
                        return bytes()
            __progress_mark = 8
            for __tmp_idx_list1 in __data_template_found:
                __progress_mark = 9
                if __data_template_found.count(__tmp_idx_list1) != 1:
                    self.decode_error = True
                    self.decode_error_text = "must be only 1 entry of the key in template"
                    return bytes()
                __progress_mark = 10
                if __tdict["snd"]["prms"][__tmp_idx_list1]["pid"] == "M":
                    __progress_mark = 101
                    if repr(snd_dict["prms"][__tmp_idx_list1]["val"]) == "-1":
                        self.decode_error = True
                        self.decode_error_text = "values in ['val'] for mandatory fields 'M' must be filled with appropriate value"
                        return bytes()
            # Here the main block - unpacking the data from snd_dict to
            # the __data_bytes_out output
            __progress_mark = 11
            for __iter_keys in snd_dict["prms"].keys():
                __progress_mark = 12
                __prm = __tdict["snd"]["prms"][__iter_keys]
                __progress_mark = 13
                __val_src = snd_dict["prms"][__iter_keys]["val"]
                __prm_data_bytes = bytes()
                __progress_mark = 14
                if __prm["is-fixed-len"] not in [True, False]:
                    self.decode_error = True
                    self.decode_error_text = "Template error - 'is-fixed-len' must be true or false"
                    return bytes()
                __progress_mark = 15
                __len = int(__prm["len"])
                __progress_mark = 16
                if (__len <= 0) and __prm["is-fixed-len"]:
                    self.decode_error = True
                    self.decode_error_text = "Template error - 'len' must be positive integer"
                __progress_mark = 17
                if __prm["type"] not in ["U8", "U16", "U32"]:
                    self.decode_error = True
                    self.decode_error_text = "Template error - 'type' must be U8, U16 or U32"
                    return bytes()
                # Here block to parse 'val' parameter
                __progress_mark = 18
                if isinstance(__val_src, int):
                    __progress_mark = 19
                    if __val_src >= 0:
                        __progress_mark = 20
                        __val = __val_src.to_bytes(int(__prm["type"][1:]) // 8, 'big')
                    else:
                        self.decode_error = True
                        self.decode_error_text = "Value of 'val' in snd_dict['prms'] must be positive: " + repr(__val_src)
                        return bytes()
                    __progress_mark = 21
                elif isinstance(__val_src, str):
                    __progress_mark = 22
                    __val = bytes.fromhex(__val_src)
                    __progress_mark = 23
                    if (len(__val) != __len) and __prm["is-fixed-len"]:
                        self.decode_error = True
                        self.decode_error_text = "Length of 'val' in snd_dict['prms']: " + repr(__val_src) + " not equal to 'len' = " + str(__len)
                        return bytes()
                else:
                    self.decode_error = True
                    self.decode_error_text = "Wrong type of 'val' in snd_dict['prms']: " + repr(__val_src)
                    return bytes()
                __progress_mark = 24
                # Checking parameter type
                if __prm["pid"] == "M":
                    # For mandatory fields with parameter id = "M"
                    pass
                else:
                    # For optional fields with parameter ids = 0x01, 0x02, etc.
                    __progress_mark = 25
                    __prmpid = int(__prm["pid"], 16)
                    __progress_mark = 26
                    if (__prmpid <= 0) or (__prmpid > 255):
                        self.decode_error = True
                        self.decode_error_text = "Template error - 'pid' must be 'M' or hex string convertable to positive 1-byte int()"
                    # Add optional parameter id
                    __progress_mark = 27
                    __prm_data_bytes += bytes([__prmpid])
                # Add 2 byte len if needed
                __progress_mark = 28
                if not __prm["is-fixed-len"]:
                    __progress_mark = 29
                    __prm_data_bytes += len(__val).to_bytes(2, 'big')
                # Add value bytes
                __progress_mark = 30
                __prm_data_bytes += __val
                # And - finally - add to the __data_bytes_out:
                __progress_mark = 31
                __data_bytes_out += __prm_data_bytes
                # Erase temporary __prm_data_bytes
                del __prm_data_bytes
        except Exception as __exc_error_descr:
            self.decode_error = True
            self.decode_error_text = "Error '" + repr(__exc_error_descr) + "' while packing at __progress_mark = " + repr(__progress_mark)
            return bytes()
        # And return from the method
        return __data_bytes_out
    def unpackToRcvDict(self, rcv_dict):
        """
        Unpack the frame data from rcv_dict.
        rcv_dict - dict() of the format:
        rcv_dict["frame"] = tuple() = (ClouRFIDFrame.message_id, ClouRFIDFrame.message_type, ClouRFIDFrame.init_by_reader)
        rcv_dict["data"] = data_bytes in the same format
        and purpose as in ClouRFIDFrame().encodeDict()
        Output is a dict() representing the top "rcv" key of the command template JSON.
        """
        self.decode_error = False
        self.decode_error_text = str()
        __output_rcv_dict = dict()
        __progress_mark = int()
        try:
            __output_rcv_dict["msid"] = self.DECODE_MID[rcv_dict["frame"][1]][rcv_dict["frame"][2]][rcv_dict["frame"][0]]
            __output_rcv_dict["mtyp"] = self.DECODE_PARAM_HEADER_TYPE[rcv_dict["frame"][1]]
            __output_rcv_dict["init"] = self.DECODE_PARAM_HEADER_INIT[rcv_dict["frame"][2]]
            __output_rcv_dict["prms"] = dict()
            __cloutemplates_file = open(self.__cloutemplates_dir + "/" + __output_rcv_dict["msid"] + ".json", "r")
            __progress_mark = 1
            __tdict = load(__cloutemplates_file, encoding="utf-8")
            __progress_mark = 2
            __cloutemplates_file.close()
            # Looking for all entries of '[]' template in "tmpl" key of the "snd" JSON
            __progress_mark = 3
            # Parse temlate string ["rcv"]["tmpl"]
            __data_template_found = re_findall("\[(\S+?)\]", __tdict["rcv"]["tmpl"])
            __progress_mark = 4
            # Data bytes got from ClouRFIDFrame().decodeDict()
            __data_bytes = rcv_dict["data"]
            # Position index in the received data bytes
            __line_index = 2
            # Index in the list - use index bcs inside the loop there can be index increments
            for __tmp_idx_list0 in __data_template_found:
                __progress_mark = 5
                # If parameter not mandatory ("M") then it is optional, and the first byte
                # at __line_index is a ["pid"] of the parameter,
                if __tdict["rcv"]["prms"][__tmp_idx_list0]["pid"] != "M":
                    __progress_mark = 6
                    # Read the value of pid in the real data
                    __opt_pid = __data_bytes[__line_index]
                    __line_index += 1   # Skip the optional pid byte
                    # so, if pid is optional, look for the dict() for this pid in templates
                    # If __prm will still be None after following cycle,
                    #then means that pid not found at all
                    __prm = None
                    for __tmp_idx_list2 in __data_template_found:
                        __progress_mark = 61
                        if int(__tdict["rcv"]["prms"][__tmp_idx_list2]["pid"], 16) == __opt_pid:
                            # __prm we take from template reference
                            __progress_mark = 62
                            __prm = __tdict["rcv"]["prms"][__tmp_idx_list2]
                    if __prm is None:
                        __progress_mark = 1001
                        raise Exception
                else:
                    __prm = __tdict["rcv"]["prms"][__tmp_idx_list0]
                # Here is the unpack block
                # Calculate the expected len of parameter data
                if __prm["is-fixed-len"]:
                    __progress_mark = 7
                    __prm_len = __prm["len"]
                else:
                    __prm_len = __data_bytes[__line_index] * 256 + __data_bytes[__line_index + 1]
                    __line_index += 2   # Skip 2 bytes of length parameter of variable len
                __progress_mark = 8
                __prm_val_raw = __data_bytes[__line_index:(__line_index + __prm_len)]
                __line_index += __prm_len
                __progress_mark = 9
                if __prm["is-fixed-len"] and (__prm_len <= 4):
                    # If fixed length parameter but not longer than 4 bytes - transform directly to int
                    __progress_mark = 10
                    __prm_val = int.from_bytes(__prm_val_raw, 'big')
                elif __prm["is-fixed-len"] and (__prm_len > 4):
                    # If fixed length parameter longer than 4 bytes - transform directly to hex string representation
                    __progress_mark = 101
                    __prm_val = str().join(format(idx_hex_conv, '02X') for idx_hex_conv in __prm_val_raw)
                elif (not __prm["is-fixed-len"]) and (__prm["type"] in ["U8"]):
                    # If variable len parameter and U8 format - transform to hex string representation
                    __progress_mark = 11
                    __prm_val = str().join(format(idx_hex_conv, '02X') for idx_hex_conv in __prm_val_raw)
                elif (not __prm["is-fixed-len"]) and (__prm["type"] in ["U16", "U32"]):
                    # If variable len parameter and U16 or U32 format - transform to list of int
                    __prm_val = list()
                    __progress_mark = 12
                    for __idx in range(len(__prm_val_raw) // (int(__prm["type"][1:]) // 8)):
                        __progress_mark = 13
                        __idx_beg = __idx * (int(__prm["type"][1:]) // 8)
                        __progress_mark = 14
                        __idx_end = __idx_beg + (int(__prm["type"][1:]) // 8)
                        __progress_mark = 15
                        __prm_val.append(int.from_bytes(__prm_val_raw[__idx], 'big'))
                # Write template dict with real extracted value to the output
                __progress_mark = 16
                __output_rcv_dict["prms"][__tmp_idx_list0] = __prm
                __progress_mark = 17
                __output_rcv_dict["prms"][__tmp_idx_list0]["val"] = __prm_val
                __progress_mark = 18
                if __line_index == len(__data_bytes):
                    break
        except Exception as __exc_error_descr:
            self.decode_error = True
            self.decode_error_text = "Error " + repr(__exc_error_descr) + " (__progress_mark = " + repr(__progress_mark) + ") unpacking frame: " + repr(rcv_dict)
            return dict()
        return __output_rcv_dict
