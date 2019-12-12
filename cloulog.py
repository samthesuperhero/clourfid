"""
Module for logging events for clouweb and cloucon applications.
Offers a convinient class helping to log any events
in different ways: files in folders, print to terminal.
Initialized with folder name where to put log files.
Using system time to log timestamps, timezone can be set manually
with public class property.
Dependent on modules: os
"""
from os import access as os_access
from os import F_OK as os_F_OK
from time import strftime, gmtime, time

class ClouLogging:
    """ Main and the only class in the module """
    def __init__(self, log_dir_path_set):
        assert isinstance(log_dir_path_set, str), "log_dir_path_set must be str()"
        assert log_dir_path_set != str(), "log_dir_path_set length must be > 0"
        assert os_access("/" + log_dir_path_set.strip("/"), os_F_OK), log_dir_path_set + " does not exist"
        self.__log_dir_path = "/" + log_dir_path_set.strip("/")
    def log(self, message_text, rfid_frame_object = 0, result_resp = 0, put_timestamp = True):
        log_text_out = list()
        s_tmp = str()
        if put_timestamp:
            tmp_time_stamp = time()
            tmp_gmtime_stamp = gmtime(tmp_time_stamp)
            s_tmp = s_tmp + strftime("[ %d.%m.%Y %H:%M:%S." + str(tmp_time_stamp - int(tmp_time_stamp))[2:8] + " UTC ] > ", tmp_gmtime_stamp) + message_text
            del tmp_time_stamp, tmp_gmtime_stamp
        else:
            s_tmp = s_tmp + message_text
        if isinstance(rfid_frame_object, ClouRFIDFrame):
            s_tmp = s_tmp + " [ " + DECODE_FRAME_ERRORS[result_resp] + " ] "
            s_tmp = s_tmp + "[ " + rfid_frame_object.message_id + " ] "
            s_tmp = s_tmp + "[ " + DECODE_PARAM_HEADER_INIT[rfid_frame_object.init_by_reader] + " ] "
            s_tmp = s_tmp + "[ " + DECODE_PARAM_HEADER_RS485[rfid_frame_object.rs485_mark] + " ] "
            s_tmp = s_tmp + "[ " + DECODE_PARAM_HEADER_TYPE[rfid_frame_object.message_type] + " ] "
            s_tmp = s_tmp + "[ DATA LEN = " + "{0:02X}".format(len(rfid_frame_object.data_bytes)) + " ]"
            s_tmp = s_tmp + " [ "
            j = 0
            for j in range(len(rfid_frame_object.data_bytes)):
                s_tmp = s_tmp + "{0:02X}".format(rfid_frame_object.data_bytes[j]) + " "
            s_tmp = s_tmp + "]"
        log_text_out.append(s_tmp)
        del s_tmp
        j = 0
        post_log_message_RLock.acquire()                       
        log_file = open(this_app_logpath + "clou-rfid-connector-" + str(app_running_ID) + strftime("-%Y-%m-%d-%H.log", gmtime()), "a")
        for j in range(len(log_text_out)):
            if log_to_stdout: print(log_text_out[j])  # Here change the way of logging !
            log_file.write(log_text_out[j].replace("\r", str()) + "\n")
        log_file.close()
        post_log_message_RLock.release()                       
        del(j, log_text_out)
