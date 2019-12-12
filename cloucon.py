"""
Application cloucon,
connector component for establishing connection
with Clou Hopeland RFID readers.
This application is built on the Clou Hopeland
proprietary reader connection protocol.

python37 /usr/share/dev/clouweb/cloucon.py msk_cl7206b2 /usr/share/dev/clouweb/clou.conf +0300 &
https://stackoverflow.com/questions/4465959/python-errno-98-address-already-in-use
https://stackoverflow.com/questions/337115/setting-time-wait-tcp
sudo tcpdump -nn -vv -A "tcp and (not dst port 22) and (not src port 22) and ((src host 178.176.12.1) or (dst host 178.176.12.1))"

"""
from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR, SOL_SOCKET, SO_REUSEADDR, timeout, setdefaulttimeout
from time import time, strftime, gmtime
from sys import argv
from json import load
from copy import deepcopy
import os
import ntplib
import clouprotocol
import fme

# First command line argument is self reader ID = parameter rid in API
own_instance_id = str(argv[1])

# Second command line argument is a file name of config file
conf_file_name = str(argv[2])

# Third command line argument is a timezone to use for logging everything
# in the form +0000 or -0000, Moscow time is +0300
log_time_zone_str = str(argv[3])
__tz = float()
try:
    __tzh = int(log_time_zone_str[1:3])
    __tzm = int(log_time_zone_str[3:5])
    if log_time_zone_str[0] == "-":
        __tz = (-1.00) * (float(__tzh) + float(__tzm / 60))
    else:
        __tz = (+1.00) * (float(__tzh) + float(__tzm / 60))
    del __tzh, __tzm
except Exception:
    print("Wrong timezone setting given in command line argument " + log_time_zone_str)
    print("Exiting the process")
    exit()
# Here timezone in float format
log_time_zone = float(__tz)
del __tz

# Open the config file
try:
    config_fd = open(conf_file_name, "r")
except Exception:
    print("Can't open config file " + conf_file_name)
    print("Exiting the process")
    exit()

# Read and decode the JSON from the config file
try:
    cfg = load(config_fd)
except Exception:
    print("Can't read / decode the JSON from config file " + conf_file_name)
    print("Exiting the process")
    exit()

# Create multiple timers dict and register the uptime
timers_dict = {
    "process-up-since": time(),
    "reader-last-act-time": None,
    "time-since-clock-check": None,
    "reader-connected-since": None,
    "reader-disconnected-since": None
}

# Close config file
try:
    config_fd.close()
except Exception:
    print("Can't close config file " + conf_file_name)
    print("Exiting the process")
    exit()

# Launch the logging instance
log = clouprotocol.ClouLogging(cfg["log-dir"], "cloucon-" + own_instance_id, timezone_set=log_time_zone_str, log_stdout_set=False)
log.log("Launched app!")
log.log("rid = [" + own_instance_id + "]")
log.log("conf file = " + conf_file_name)
print("\nLaunched app!\n")

# Check reader ID in config
if own_instance_id not in cfg["readers-list"]:
    log.log("rid = [" + own_instance_id + "] not set in config list, exiting the process")
    log.log("Exiting the process")
    exit()
else:
    if own_instance_id not in cfg.keys():
        log.log("rid = [" + own_instance_id + "] set in config list, but settings key not found, exiting the process")
        log.log("Exiting the process")
        exit()

try:
    reply_from_reader_timeout = float(cfg["reply-from-reader-timeout"])
except Exception:
    log.log('Can not load ["reply-from-reader-timeout"] from config')
    log.log("Exiting the process")
    exit()

# Create specific dict() for reader parameters for rid = own_instance_id
cfgrid = cfg[own_instance_id]

# NTP clock check
try:
    ntp_check_interval = cfgrid["ntp-check-interval"]
    ntp_check_log = list()
    ntp_service = ntplib.NTPClient()
    ntp_service_response = ntp_service.request(cfg["ntp-service-url"], version=3)
    if abs(ntp_service_response.offset) > cfg["max-server-time-offset"]:
        log.log('Server time too far from NTP time at ' + cfg["ntp-service-url"] + ', offset = ' + repr(ntp_service_response.offset))
        log.log("Exiting the process")
        exit()
    timers_dict["time-since-clock-check"] = time()
    ntp_check_log.append(abs(ntp_service_response.offset))
except Exception as __exc_error_descr:
    log.log("Error checking clock via NTP service" + repr(__exc_error_descr))
    log.log("Exiting the process")
    exit()

# Set basic sockets for server socket
setdefaulttimeout(cfgrid["sock-timeout"])
log.log("Expecting that reader is in " + cfgrid["reader-mode"] + " mode")
if cfgrid["reader-mode"] == "client":
    srv_basic_sock = socket(AF_INET, SOCK_STREAM)
    srv_basic_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    srv_basic_sock.bind((cfgrid["host"], cfgrid["port"]))
    srv_basic_sock.listen(1)
    log.log("Listening for incoming connection at " + cfgrid["host"] + ":" + str(cfgrid["port"]))
elif cfgrid["reader-mode"] == "server":
    rid_sock = socket(AF_INET, SOCK_STREAM)
    log.log("Connecting to " + cfgrid["host"] + ":" + str(cfgrid["port"]))
else:
    log.log("Unknown reader-mode: " + cfgrid["reader-mode"] + ", exiting the process")
    exit()

# Create main SessionState instance
session_state = clouprotocol.SessionState()

# Create raw stream processing instance
raw_stream = clouprotocol.ReceivedRawLine(cfgrid["parse-limit"])

# Create frame list for priority sending to reader - replying on urgent confirmation requests from reader
frames_line_to_snd_1st = bytes() # 1st priority

# Create frame list for standard priority sending to reader
frames_line_to_snd_std = bytes() # 1st priority

# Create the decoded frames list, this will be a list of dicts containing received
# and decoded frames but not yet processed and not yet matched as replies from
# reader on previously sent request frames
decoded_frames_list_dicts = list()

# Create list of API requests tuples, first "to send" buffer list, second - "successfully sent"
# buffer for further processing; in each tuple the info about time, request ID from web,
# the content of request, etc.; next step - matching incoming frames from reader with the
# list of "successfully sent" tuples in chrono order - from oldest to latest, by MID and if ERR_WARN
# as well
queue_to_send = list()
queue_sent = list()

# Create lists of frames dicts for further logging
frames_to_log_list_received = list()    # List of dicts received from reader - further used only for logging
frames_to_log_list_sent = list()        # List of dicts sent to reader - further used only for logging
std_frames_to_log_list_sent = list()        # List of dicts sent to reader - further used only for logging

# Create ClouRFIDFrame() instance for encoding / decoding frames
rfidframe = clouprotocol.ClouRFIDFrame()

# This is just for logging purposes
rfidframe_tolog = clouprotocol.ClouRFIDFrame()
tagframe_tolog = clouprotocol.TagData()

# Create TagData() instance for decoding tag data frames
tagframe = clouprotocol.TagData()

# Create tag buffer for storing read tags
tag_buf = list()
tag_buf_match_duplicates = list()

# Create ClouProtocolDefinitions() instance
D = clouprotocol.ClouProtocolDefinitions()

# Create dict() for general command reference
cmd_ref_dict = dict()

# Import command JSONs from commands dir into command reference
try:
    for __tmp_root, __tmp_dirs, __tmp_files in os.walk("/" + cfg["cmds-dir"].strip("/")):
        for __tmp_name_walk_f in __tmp_files:
            if (__tmp_name_walk_f[:-5] in D.FULL_MID_LIST) and (__tmp_name_walk_f[-5:] == ".json"):
                __json_file = open(os.path.join(__tmp_root, __tmp_name_walk_f), "r")
                cmd_ref_dict[__tmp_name_walk_f[:-5]] = load(__json_file)
                __json_file.close()
except Exception:
    log.log("Error reading and unpacking JSON from file(s) in /" + cfg["cmds-dir"].strip("/") + ", exiting the process")
    exit()

# Create PackDataToClou() instance
packframes = clouprotocol.PackDataToClou(cfg["cmds-dir"])

# Create FileMessageExchange() instance
fme_msg = fme.FileMessageExchange(str(own_instance_id), ("/" + cfg["clou-run"].strip("/") + "/" + str(own_instance_id)), message_types_set=["CLU", "STS"])

# Create lists for storing received API requests from web API of two types
# CLU for clou protocol queries, STS for status queries
fme_CLU_recv_list = list()
fme_STS_recv_list = list()

# =================== MAIN LOOP START ===================
while True:

    # If not connected
    if not session_state.connected:
        # Connection procedure
        try:
            if cfgrid["reader-mode"] == "client":
                rid_sock, rid_accepted_addr = srv_basic_sock.accept()
                log.log('Accepted connection from ' + rid_accepted_addr[0] + ":" + str(rid_accepted_addr[1]) + "!")
            elif cfgrid["reader-mode"] == "server":
                rid_sock.connect((cfgrid["host"], cfgrid["port"]))
                log.log('Connected to reader ' + cfgrid["host"] + ":" + str(cfgrid["port"]) + "!")
            session_state.connected = True
            timers_dict["reader-connected-since"] = time()
            timers_dict["reader-last-act-time"] = time()
            timers_dict["reader-disconnected-since"] = None
        except Exception as sock_exception_err:
            session_state.connected = False
            if not isinstance(sock_exception_err, timeout):
                timers_dict["reader-connected-since"] = None
                timers_dict["reader-disconnected-since"] = None
                log.log("Error during establishing connection")

    # If connected
    elif session_state.connected:

        # Reading incoming stream from scanner
        recv_chunk = bytes()
        recv_chunk_time_to_log = float()
        try:
            recv_chunk = rid_sock.recv(2**12)   # Recieve data from socket
            if recv_chunk:
                recv_chunk_time_to_log = time()
                timers_dict["reader-last-act-time"] = recv_chunk_time_to_log
        except Exception as sock_read_err:
            recv_chunk = bytes()
            if not isinstance(sock_read_err, timeout):
                session_state.connected = False
                timers_dict["reader-connected-since"] = None
                timers_dict["reader-disconnected-since"] = time()
                log.log("Lost connection!")

        # If received data not empty, add it to the stream processing instance
        try:
            if recv_chunk:
                raw_stream.add_to_stream(recv_chunk)
        except Exception:
            log.log("Error adding recv_chunk to ReceivedRawLine() instance")

        # Clean up the chunk bytes() instance
        del recv_chunk

        # Unpack received data into frames straight now
        try:
            if raw_stream.unpack() == -1:
                log.log("Reported error from unpack(): " + raw_stream.geterr())
        except Exception:
            log.log("Error in try: except: in cloucon.py while unpacking")

        # Log unknown bytes
        unpack_unknowns = raw_stream.get_unknowns()
        for unpack_unknowns_bytes in unpack_unknowns:
            log.log("Unknown bytes received from reader: [" + " ".join(format(idx_hex_conv, '02X') for idx_hex_conv in unpack_unknowns_bytes) + " ]")

        # Decoding all packets received in raw_stream.frames by types,
        # and putting them in list of dict() called decoded_frames_list_dicts:
        frames_to_log_list_received = list()    # logging list
        for idx_prc_frm in range(len(raw_stream.frames)):
            rfidframe.clear()
            rfidframe.frame_raw_line = raw_stream.frames.pop(0)
            decode_frame_res = rfidframe.decodeFrame()
            tmp_dict_frame = dict()
            tmp_dict_frame["res"] = decode_frame_res    # int() result of frame
            tmp_dict_frame["frame"] = (rfidframe.message_id, rfidframe.message_type, rfidframe.init_by_reader)
            tmp_dict_frame["data"] = rfidframe.data_bytes   # data_bytes, can contain 2 len bytes or not - depends on MID!
            tmp_dict_frame["recv-time"] = recv_chunk_time_to_log
            if tmp_dict_frame["res"] == 0:
                decoded_frames_list_dicts.append(tmp_dict_frame)
            frames_to_log_list_received.append(tmp_dict_frame)
            del tmp_dict_frame

        # raw_stream.frames should be already empty!
        if raw_stream.frames:
            log.log("Error: raw_stream.frames not empty after decoding")

        # Now going through decoded_frames_list_dicts first filter out priority
        # frames and instantly composing bytes line with answer to reader
        tmp_decoded_frames_list_dicts = list()
        for idx_prc_frm in range(len(decoded_frames_list_dicts)):
            fr_dict_prc = decoded_frames_list_dicts.pop(0)
            # Regular MAN_READER_CONN_CONFIRM 'pings' from Clou reader due to protocol
            if (fr_dict_prc["frame"] == (D.MAN_READER_CONN_CONFIRM, D.TYPE_CONF_MANAGE, D.INIT_BY_READER)) and (fr_dict_prc["res"] == 0):
                if (len(fr_dict_prc["data"]) == 6) and (fr_dict_prc["data"][0] == 0x00) and (fr_dict_prc["data"][1] == 0x04):
                    # Means, we work on reply only if the len of data bytes condition True,
                    # otherwise just ignore this incoming message from reader
                    rfidframe.clear()
                    rfidframe.message_id = D.MAN_CONN_CONFIRM
                    rfidframe.message_type = D.TYPE_CONF_MANAGE
                    rfidframe.init_by_reader = D.INIT_BY_USER
                    rfidframe.data_bytes = fr_dict_prc["data"][2:6]
                    rfidframe.encodeFrame()
                    # Here - append frame to the raw lite to send with high priority!
                    frames_line_to_snd_1st += rfidframe.frame_raw_line
                    # and here - append frame dict to the list for further logging
                    # log message to send
                    frames_to_log_list_sent.append({"frame": (D.MAN_CONN_CONFIRM, D.TYPE_CONF_MANAGE, D.INIT_BY_USER), "data": fr_dict_prc["data"][2:6], "res": 0})
            # After receiving the tag data frame always need to confirm that to Clou reader due to protocol
            elif (fr_dict_prc["frame"] == (D.OP_READER_EPC_DATA_UPLOAD, D.TYPE_CONF_OPERATE, D.INIT_BY_READER)) and (fr_dict_prc["res"] == 0):
                tagframe.decodeTag(fr_dict_prc["data"])
                if not tagframe.decode_error:
                    # If tag data decoded correctly, store the unique tag in the tag_buf
                    __tag_dict_to_buf = dict()
                    __tag_dict_to_buf_match_duplicates = dict()
                    try:
                        __tag_dict_to_buf = tagframe.encodeInDict()
                        __tag_dict_to_buf_match_duplicates = deepcopy(__tag_dict_to_buf)
                        __tag_prms_item = str()
                        for __tag_prms_item in cfg["tag-param-duplicate-exclude"]:
                            del __tag_dict_to_buf_match_duplicates["params"][__tag_prms_item]
                        del __tag_prms_item
                    except Exception:
                        pass
                    if __tag_dict_to_buf_match_duplicates not in tag_buf_match_duplicates:
                        tag_buf.append(__tag_dict_to_buf)
                        tag_buf_match_duplicates.append(__tag_dict_to_buf_match_duplicates)
                    del __tag_dict_to_buf, __tag_dict_to_buf_match_duplicates
                    # If tag data decoded correctly, build the answer to reader
                    if 0x08 in tagframe.params.keys():
                        rfidframe.clear()
                        rfidframe.message_id = D.MAN_TAG_DATA_RESPONSE
                        rfidframe.message_type = D.TYPE_CONF_MANAGE
                        rfidframe.init_by_reader = D.INIT_BY_USER
                        rfidframe.data_bytes = tagframe.params[0x08]
                        rfidframe.encodeFrame()
                        frames_line_to_snd_1st += rfidframe.frame_raw_line
                        # log message to send
                        frames_to_log_list_sent.append({"frame": (D.MAN_TAG_DATA_RESPONSE, D.TYPE_CONF_MANAGE, D.INIT_BY_USER), "data": tagframe.params[0x08], "res": 0})
                else:
                    # If tag data decoding problem - leave the frame for future analysis
                    tmp_decoded_frames_list_dicts.append(fr_dict_prc)
            else:
                tmp_decoded_frames_list_dicts.append(fr_dict_prc)

        # raw_stream.frames should be already empty!
        if decoded_frames_list_dicts:
            log.log("Error: decoded_frames_list_dicts not empty after priority frames filtering")

        # Finally substituting list decoded_frames_list_dicts with frames dicts left after filtering
        # This will be the list of frames to analyze below to search for answers from reader
        # on previous frames that were sent to reader by this process
        decoded_frames_list_dicts = list()
        decoded_frames_list_dicts = deepcopy(tmp_decoded_frames_list_dicts)
        del tmp_decoded_frames_list_dicts

        # Here send the first priority reply to reader =======
        sent_all_time_to_log = float()
        sent_success_flag = False
        if len(frames_line_to_snd_1st) > 0:
            try:
                # Here send!
                if rid_sock.sendall(frames_line_to_snd_1st) is None:
                    sent_success_flag = True
                    sent_all_time_to_log = time()
                    # If sent successfully - clear buffer
                    frames_line_to_snd_1st = bytes()
            except Exception as sock_read_err:
                if not isinstance(sock_read_err, timeout):
                    session_state.connected = False
                    timers_dict["reader-connected-since"] = None
                    timers_dict["reader-disconnected-since"] = time()
                    log.log("Lost connection!")

        # And log all received
        tmp_log_tag_frames_count = int()
        for idx_prc_frm in range(len(frames_to_log_list_received)):
            rfidframe_tolog.clear()
            rfidframe_tolog.message_id = frames_to_log_list_received[idx_prc_frm]["frame"][0]
            rfidframe_tolog.message_type = frames_to_log_list_received[idx_prc_frm]["frame"][1]
            rfidframe_tolog.init_by_reader = frames_to_log_list_received[idx_prc_frm]["frame"][2]
            rfidframe_tolog.data_bytes = frames_to_log_list_received[idx_prc_frm]["data"]
            if (frames_to_log_list_received[idx_prc_frm]["frame"] == (D.OP_READER_EPC_DATA_UPLOAD, D.TYPE_CONF_OPERATE, D.INIT_BY_READER)) and (frames_to_log_list_received[idx_prc_frm]["res"] == 0):
                if cfgrid["log-tag-frames"]:
                    tagframe_tolog.decodeTag(rfidframe_tolog.data_bytes)
                    log.log("Received from reader", instance_to_log=rfidframe_tolog, explicit_timestamp=recv_chunk_time_to_log, result_resp=frames_to_log_list_received[idx_prc_frm]["res"])
                    log.log(str(), instance_to_log=tagframe_tolog, put_timestamp=False)
                else:
                    tmp_log_tag_frames_count += 1
            else:
                log.log("Received from reader", instance_to_log=rfidframe_tolog, explicit_timestamp=recv_chunk_time_to_log, result_resp=frames_to_log_list_received[idx_prc_frm]["res"])
        if tmp_log_tag_frames_count > 0:
            log.log("Received from reader " + str(tmp_log_tag_frames_count) + " tag data frames", explicit_timestamp=recv_chunk_time_to_log)
        frames_to_log_list_received = list()
        del tmp_log_tag_frames_count

        # and log urgent sent messages
        if sent_success_flag:
            tmp_log_tag_frames_count = int()
            for idx_prc_frm in range(len(frames_to_log_list_sent)):
                rfidframe_tolog.clear()
                rfidframe_tolog.message_id = frames_to_log_list_sent[idx_prc_frm]["frame"][0]
                rfidframe_tolog.message_type = frames_to_log_list_sent[idx_prc_frm]["frame"][1]
                rfidframe_tolog.init_by_reader = frames_to_log_list_sent[idx_prc_frm]["frame"][2]
                rfidframe_tolog.data_bytes = frames_to_log_list_sent[idx_prc_frm]["data"]
                if frames_to_log_list_sent[idx_prc_frm]["frame"] == (D.MAN_TAG_DATA_RESPONSE, D.TYPE_CONF_MANAGE, D.INIT_BY_USER):
                    if cfgrid["log-tag-frames"]:
                        log.log("Sent to reader", instance_to_log=rfidframe_tolog, explicit_timestamp=sent_all_time_to_log)
                    else:
                        tmp_log_tag_frames_count += 1
                else:
                    log.log("Sent to reader", instance_to_log=rfidframe_tolog, explicit_timestamp=sent_all_time_to_log)
            if tmp_log_tag_frames_count > 0:
                log.log("Sent to reader " + str(tmp_log_tag_frames_count) + " tag data frame confirmations", explicit_timestamp=sent_all_time_to_log)
            frames_to_log_list_sent = list()
            del tmp_log_tag_frames_count

        # Cleanup
        del sent_all_time_to_log, sent_success_flag

        # Here we process clou type of web requests
        # First assure having the chronological order
        try:
            __tmp_fme_recv_list = list()
            __tmp_fme_recv_list = sorted(fme_CLU_recv_list, key=lambda __key: __key[1])
            fme_CLU_recv_list = list()
            fme_CLU_recv_list = deepcopy(__tmp_fme_recv_list)
            del __tmp_fme_recv_list
        except Exception:
            log.log("Error sorting fme_CLU_recv_list list")
        # Then here processing of incoming API requests for CLU type
        fme_CLU_recv_list_item = tuple()
        fme_CLU_recv_list_len = len(fme_CLU_recv_list)
        # Progress counter for logging sensitive parsing possible break point
        __progress_snd_CLU = int()
        for __tmp_idx_fme in range(fme_CLU_recv_list_len):
            try:
                __progress_snd_CLU = 1
                fme_CLU_recv_list_item = fme_CLU_recv_list.pop(0)
                __progress_snd_CLU = 2
                __snd_val_dict = fme_CLU_recv_list_item[0]["query-content"]
                __progress_snd_CLU = 3
                __snd_to_snd_dict = cmd_ref_dict[__snd_val_dict["msid"]]["snd"]
                __progress_snd_CLU = 4
                __copy_tmp_dict = deepcopy(__snd_to_snd_dict["prms"])
                for __prms_item_key in __copy_tmp_dict.keys():
                    __progress_snd_CLU = 5
                    if __prms_item_key in __snd_val_dict["prms"].keys():
                        __progress_snd_CLU = 6
                        __snd_to_snd_dict["prms"][__prms_item_key]["val"] = __snd_val_dict["prms"][__prms_item_key]["val"]
                    else:
                        if __snd_to_snd_dict["prms"][__prms_item_key]["pid"] != "M":
                            # Remove whole key for optional parameter not present in __snd_val_dict
                            # if this parameter is not mandatory
                            __progress_snd_CLU = 7
                            del __snd_to_snd_dict["prms"][__prms_item_key]
                        else:
                            # And if the parameter was mandatory going for exception
                            __progress_snd_CLU = 1001
                            raise Exception
                del __copy_tmp_dict
                rfidframe.clear()
                __progress_snd_CLU = 8
                rfidframe.message_type = D.PARAM_HEADER_TYPE[__snd_to_snd_dict["mtyp"]]
                __progress_snd_CLU = 9
                rfidframe.init_by_reader = D.PARAM_HEADER_INIT[__snd_to_snd_dict["init"]]
                __progress_snd_CLU = 10
                rfidframe.message_id = D.MID[rfidframe.message_type][rfidframe.init_by_reader][__snd_to_snd_dict["msid"]]
                __progress_snd_CLU = 11
                rfidframe.data_bytes = packframes.packFromSndDict(__snd_to_snd_dict)
                __progress_snd_CLU = 12
                if packframes.decode_error:
                    # In case of packing error we just log it, skip and forget this message received from API
                    __progress_snd_CLU = 13
                    log.log("Error packframes.packFromSndDict() " + packframes.decode_error_text + ": " + repr(__snd_to_snd_dict))
                    rfidframe.clear()
                else:
                    __progress_snd_CLU = 14
                    rfidframe.encodeFrame()
                    frames_line_to_snd_std += rfidframe.frame_raw_line
                    # Add the message planned to send to main queue == reader <-> this app == exchange
                    queue_to_send.append(fme_CLU_recv_list_item)
                    # And log message to send
                    __progress_snd_CLU = 15
                    std_frames_to_log_list_sent.append({"frame": (rfidframe.message_id, rfidframe.message_type, rfidframe.init_by_reader), "data": rfidframe.data_bytes, "res": 0})
            except Exception as __exc_error_descr:
                log.log("Error '" + repr(__exc_error_descr) + "' processing API command from web at __progress_snd_CLU = " + repr(__progress_snd_CLU) + ": " + repr(fme_CLU_recv_list_item))
        # Some cleanup
        del fme_CLU_recv_list_item, fme_CLU_recv_list_len, __progress_snd_CLU

        # Here send the regular priority requests to reader =======
        std_sent_success_flag = False
        std_sent_all_time_to_log = float()
        if len(frames_line_to_snd_std) > 0:
            try:
                # Here send!
                if rid_sock.sendall(frames_line_to_snd_std) is None:
                    std_sent_success_flag = True
                    std_sent_all_time_to_log = time()
                    # If sent successfully - clear buffer
                    frames_line_to_snd_std = bytes()
            except Exception as sock_read_err:
                if not isinstance(sock_read_err, timeout):
                    session_state.connected = False
                    timers_dict["reader-connected-since"] = None
                    timers_dict["reader-disconnected-since"] = time()
                    log.log("Lost connection!")
        # And log it - and add to queue_sent!
        if std_sent_success_flag:
            for idx_prc_frm in range(len(std_frames_to_log_list_sent)):
                rfidframe_tolog.clear()
                rfidframe_tolog.message_id = std_frames_to_log_list_sent[idx_prc_frm]["frame"][0]
                rfidframe_tolog.message_type = std_frames_to_log_list_sent[idx_prc_frm]["frame"][1]
                rfidframe_tolog.init_by_reader = std_frames_to_log_list_sent[idx_prc_frm]["frame"][2]
                rfidframe_tolog.data_bytes = std_frames_to_log_list_sent[idx_prc_frm]["data"]
                log.log("Sent to reader", instance_to_log=rfidframe_tolog, explicit_timestamp=std_sent_all_time_to_log)
            std_frames_to_log_list_sent = list()
            # Adding sent requests to uqeue_sent list for further matching!
            __queue_to_send_item = tuple()
            for __queue_to_send_item in queue_to_send:
                queue_sent.append(__queue_to_send_item)
            queue_to_send = list()
            del __queue_to_send_item
        # Cleanup of temporary objects
        del std_sent_all_time_to_log, std_sent_success_flag

        # Before matching need to erase outdated commands sent to reader in queue_sent,
        # because no sense to match them as web API request already timed out
        queue_sent_item = tuple()
        __tmp_queue_sent = list()
        queue_sent_len = len(queue_sent)
        for __queue_sent_idx in range(queue_sent_len):
            queue_sent_item = queue_sent.pop(0)
            if (time() - queue_sent_item[1]) < reply_from_reader_timeout:
                __tmp_queue_sent.append(queue_sent_item)
        queue_sent = list()
        if __tmp_queue_sent:
            queue_sent = deepcopy(__tmp_queue_sent)
        del queue_sent_item, __tmp_queue_sent, queue_sent_len

        # Here we finally iterate through frames (in decoded_frames_list_dicts) received in
        # this cycle and remaining after extracting urgent messages from them, (and remaining
        # from the previous cycles as well!) and try to match these
        # frames with frames that we sent to the reader earlier - to find replies from reader.
        # We match in chronological order, match by MID, type and receive,
        # also we match error messages from reader that contain MID and length
        # indication. For more information look Clou protocol specification.
        #
        # Also we erase commands received from API and sent to reader (in queue_sent) that are
        # too old, older than "reply-from-reader-timeout" setting in clou.conf,
        # and we log frames received from reader (in decoded_frames_list_dicts) on this cycle
        # that were not matched. Means, that no frame in decoded_frames_list_dicts will go to the next
        # cycle.
        #
        # First assure having the chronological order
        try:
            __tmp_frames_list = list()
            __tmp_frames_list = sorted(decoded_frames_list_dicts, key=lambda __key: __key["recv-time"])
            decoded_frames_list_dicts = list()
            decoded_frames_list_dicts = deepcopy(__tmp_frames_list)
            del __tmp_frames_list
        except Exception:
            log.log("Error sorting decoded_frames_list_dicts list")
        # Here the iteration cycle to match, those not matched just skipped and forgot
        frames_item = dict()
        __unpack_dict = dict()
        __tmp_idx_frames_list = int()
        __match_tuple = tuple()
        decoded_frames_list_dicts_len = len(decoded_frames_list_dicts)
        for __tmp_idx_frames_list in range(decoded_frames_list_dicts_len):
            # Pop the first element from the list of frames received from reader
            frames_item = decoded_frames_list_dicts.pop(0)
            # Unpack this frame to template "rcv" formatted dict()
            __unpack_dict = packframes.unpackToRcvDict(frames_item)
            if packframes.decode_error:
                log.log("packframes.unpackToRcvDict(frames_item): " + packframes.decode_error_text)
            else:
                # Here we first extract the matching tuple from the item of decoded_frames_list_dicts
                # to match item of decoded_frames_list_dicts with items in queue_sent
                __match_tuple = tuple()
                __rcv_match_tuple = tuple()
                if __unpack_dict["msid"] == "ERR_MID":
                    # If reader replied with error
                    try:
                        rfidframe.clear()
                        rfidframe.frame_raw_line = __unpack_dict["prms"]["ctrlword"]["val"].to_bytes(2, 'big')
                        __ctrl_word_res = rfidframe.decodeCtrlWord()
                        if __ctrl_word_res != 0:
                            raise Exception
                        __match_tuple = (rfidframe.message_id, rfidframe.message_type, rfidframe.init_by_reader)
                        rfidframe.clear()
                    except Exception as __exc_error_descr:
                        log.log("Error unpacking control word of ERR_WARN message from reader: " + repr(__exc_error_descr))
                else:
                    # Use rfidframe only as temporary storage of parameters
                    rfidframe.clear()
                    rfidframe.message_type = D.PARAM_HEADER_TYPE[__unpack_dict["mtyp"]]
                    rfidframe.init_by_reader = D.PARAM_HEADER_INIT[__unpack_dict["init"]]
                    rfidframe.message_id = D.MID[rfidframe.message_type][rfidframe.init_by_reader][__unpack_dict["msid"]]
                    __match_tuple = (rfidframe.message_id, rfidframe.message_type, rfidframe.init_by_reader)
                    rfidframe.clear()
                # Now in __match_tuple we have the pattern of the frame frames_item received from reader
                # And below we search through queue_sent to get the first match
                __matched_flag = False
                queue_sent_item = tuple()
                __tmp_queue_sent = list()
                queue_sent_len = len(queue_sent)
                try:
                    for __queue_sent_idx in range(queue_sent_len):
                        queue_sent_item = queue_sent.pop(0)
                        # ! Here is the important trick: we take from template reference cmd_ref_dict
                        # the ["rcv"] key of template - BUT from the template corresponding to the
                        # ["msid"] key of queue_sent_item, means the MID of the item from queue_sent
                        # to match below:
                        __rcv_match = cmd_ref_dict[queue_sent_item[0]["query-content"]["msid"]]["rcv"]
                        # Use rfidframe only as temporary storage of parameters
                        rfidframe.clear()
                        rfidframe.message_type = D.PARAM_HEADER_TYPE[__rcv_match["mtyp"]]
                        rfidframe.init_by_reader = D.PARAM_HEADER_INIT[__rcv_match["init"]]
                        rfidframe.message_id = D.MID[rfidframe.message_type][rfidframe.init_by_reader][__rcv_match["msid"]]
                        __rcv_match_tuple = (rfidframe.message_id, rfidframe.message_type, rfidframe.init_by_reader)
                        rfidframe.clear()
                        # AND HERE FINALLY MATCH
                        if __rcv_match_tuple == __match_tuple:
                            # If matched - send the reply to API!
                            __matched_flag = True
                            msg_content_to_send = dict()
                            msg_content_to_send["web-req-id"] = queue_sent_item[0]["web-req-id"]
                            msg_content_to_send["reply-content"] = __unpack_dict
                            if fme_msg.snd(queue_sent_item[2], "CLU", msg_content_to_send) == 0:
                                log.log("Replied to web API: " + repr(__unpack_dict))
                            else:
                                log.log("Error (" + repr(fme_msg.geterr()) + ") replying to web API: " + repr(msg_content_to_send))
                            del msg_content_to_send
                        else:
                            __tmp_queue_sent.append(queue_sent_item)
                    queue_sent = list()
                    if __tmp_queue_sent:
                        queue_sent = deepcopy(__tmp_queue_sent)
                except Exception as __exc_error_descr:
                    try:
                        msg_content_to_send = dict()
                        msg_content_to_send["web-req-id"] = queue_sent_item[0]["web-req-id"]
                        msg_content_to_send["reply-content"] = {"Error": "Error (" + repr(__exc_error_descr) + ") processing queue_sent item: " + repr(queue_sent_item)}
                        if fme_msg.snd(queue_sent_item[2], "CLU", msg_content_to_send) == 0:
                            log.log("Replied error to web API")
                        else:
                            log.log("Error (" + repr(fme_msg.geterr()) + ") replying error to web API")
                        del msg_content_to_send
                    except Exception:
                        pass
                    log.log("Error (" + repr(__exc_error_descr) + ") processing queue_sent item: " + repr(queue_sent_item))
                # Here we skip and forget unmatched frame frames_item
                # extracted from decoded_frames_list_dicts
                if not __matched_flag:
                    if (__unpack_dict['msid'] == 'MAN_CONN_CONFIRM') and (__unpack_dict['mtyp'] == 'TYPE_CONF_MANAGE') and (__unpack_dict['init'] == 'INIT_BY_USER'):
                        # Not logging empty confirms on our MAN_CONN_CONFIRM confirms to reader
                        pass
                    else:
                        log.log("Warning: unmatched frame from reader skipped: " + repr(__unpack_dict))
                # Cleanup
                del __matched_flag, __match_tuple, __rcv_match_tuple, queue_sent_item, __tmp_queue_sent, queue_sent_len
        # Cleanup
        del frames_item, __tmp_idx_frames_list, decoded_frames_list_dicts_len, __unpack_dict

        # Here we check if reader is still alive, look "reader-no-life-timeout" setting in the clou.conf,
        # and if no data got from reader for more than "reader-no-life-timeout" - then close the connection manually
        if (not (timers_dict["reader-last-act-time"] is None)) and session_state.connected:
            __tmp_no_life_time = float(time() - timers_dict["reader-last-act-time"])
            if  __tmp_no_life_time > cfg["reader-no-life-timeout"]:
                try:
                    rid_sock.shutdown(SHUT_RDWR)
                    rid_sock.close()
                    session_state.connected = False
                    timers_dict["reader-connected-since"] = None
                    timers_dict["reader-disconnected-since"] = time()
                    log.log("Forced connection close due to timeout, check reader-no-life-timeout in config, reader not sending data for > " + repr(__tmp_no_life_time) + " seconds")
                except Exception:
                    log.log("Error forced connection close attempted due to timeout")
            del __tmp_no_life_time

    # Getting messages of CLU type from web for sending to reader from fme_msg
    __tmp_fme_CLU_recv_list = list()
    __fme_msg_recv_count = int()
    __fme_msg_recv_time_to_log = float()
    __fme_msg_recv_list_item = tuple()
    try:
        __fme_msg_recv_count = fme_msg.rcv("*", "CLU", cutoff_time=timers_dict["process-up-since"])
        __fme_msg_recv_time_to_log = time()
    except Exception:
        log.log("Error running fme_msg.rcv('*', 'CLU')")
    if __fme_msg_recv_count < 0:
        log.log("Error receiving fme_msg.rcv('*', 'CLU'): " + fme_msg.geterr())
    elif __fme_msg_recv_count > 0:
        __tmp_fme_CLU_recv_list = fme_msg.getall()
        for __fme_msg_recv_list_item in __tmp_fme_CLU_recv_list:
            if __fme_msg_recv_time_to_log:
                log.log("Received from web API: " + repr(__fme_msg_recv_list_item), explicit_timestamp=__fme_msg_recv_time_to_log)
    # Adding received queries to the global list
    fme_CLU_recv_list += __tmp_fme_CLU_recv_list
    # Some clean up
    fme_msg.clearall()
    del __fme_msg_recv_count, __fme_msg_recv_time_to_log, __fme_msg_recv_list_item, __tmp_fme_CLU_recv_list

    # Getting messages of STS type from web for sending to reader from fme_msg
    __tmp_fme_STS_recv_list = list()
    __fme_msg_recv_count = int()
    __fme_msg_recv_time_to_log = float()
    __fme_msg_recv_list_item = tuple()
    try:
        __fme_msg_recv_count = fme_msg.rcv("*", "STS", cutoff_time=timers_dict["process-up-since"])
        __fme_msg_recv_time_to_log = time()
    except Exception:
        log.log("Error running fme_msg.rcv('*', 'STS')")
    if __fme_msg_recv_count < 0:
        log.log("Error receiving fme_msg.rcv('*', 'STS'): " + fme_msg.geterr())
    elif __fme_msg_recv_count > 0:
        __tmp_fme_STS_recv_list = fme_msg.getall()
        for __fme_msg_recv_list_item in __tmp_fme_STS_recv_list:
            if __fme_msg_recv_time_to_log:
                log.log("Received from web API: " + repr(__fme_msg_recv_list_item), explicit_timestamp=__fme_msg_recv_time_to_log)
    # Adding received queries to the global list
    fme_STS_recv_list += __tmp_fme_STS_recv_list
    # Some clean up
    fme_msg.clearall()
    del __fme_msg_recv_count, __fme_msg_recv_time_to_log, __fme_msg_recv_list_item, __tmp_fme_STS_recv_list

    # Here we process status request types
    # First assure having the chronological order
    try:
        __tmp_fme_recv_list = list()
        __tmp_fme_recv_list = sorted(fme_STS_recv_list, key=lambda __key: __key[1])
        fme_STS_recv_list = list()
        fme_STS_recv_list = __tmp_fme_recv_list
        del __tmp_fme_recv_list
    except Exception:
        log.log("Error sorting fme_STS_recv_list list")

    fme_STS_recv_list_item = tuple()
    fme_STS_recv_list_len = len(fme_STS_recv_list)
    for __tmp_idx_fme in range(fme_STS_recv_list_len):
        __json_file_name = str()
        try:
            fme_STS_recv_list_item = fme_STS_recv_list.pop(0)
            # Preparing message to send back
            msg_content_to_send = dict()
            msg_content_to_send["web-req-id"] = fme_STS_recv_list_item[0]["web-req-id"]
            # Search through commands
            if fme_STS_recv_list_item[0]["query-content"]["api-method"] == "update":
            # === update === For method update - import command JSONs from commands dir into command reference
                __count_upd_files = int()
                __count_upd_files_list = list()
                try:
                    for __tmp_root, __tmp_dirs, __tmp_files in os.walk("/" + cfg["cmds-dir"].strip("/")):
                        for __tmp_name_walk_f in __tmp_files:
                            if (__tmp_name_walk_f[:-5] in D.FULL_MID_LIST) and (__tmp_name_walk_f[-5:] == ".json"):
                                __json_file_name = os.path.join(__tmp_root, __tmp_name_walk_f)
                                __json_file = open(__json_file_name, "r")
                                cmd_ref_dict[__tmp_name_walk_f[:-5]] = load(__json_file)
                                __json_file.close()
                                __count_upd_files += 1
                                __count_upd_files_list.append(__tmp_name_walk_f)
                    log.log("Successfully updated command reference " + str(__count_upd_files) + " files: " + repr(__count_upd_files_list))
                    msg_content_to_send["reply-content"] = {"is-ok": True, "result": ("Successfully updated command reference " + str(__count_upd_files) + " files: " + repr(__count_upd_files_list))}
                except Exception as __exc_error_descr:
                    log.log("Error updating command reference: " + repr(__exc_error_descr))
                    msg_content_to_send["reply-content"] = {"is-ok": False, "result": ("Error updating command reference: " + repr(__exc_error_descr))}
                del __count_upd_files, __count_upd_files_list
            # === shutdown === Safe process shutdown if received shutdown method
            elif fme_STS_recv_list_item[0]["query-content"]["api-method"] == "shutdown":
                session_state.global_shutdown_flag = True
                msg_content_to_send["reply-content"] = {"is-ok": True, "result": "Successfully shutting down the process"}
            # === getstatus === Reply to web API with status JSON
            elif fme_STS_recv_list_item[0]["query-content"]["api-method"] == "getstatus":
                msg_content_to_send["reply-content"] = dict()
                msg_content_to_send["reply-content"]["is-ok"] = True
                __status_dict = dict()
                # Is reader now connected
                __status_dict["reader-connected"] = session_state.connected
                # Time since the connection of reader, not empty if connected
                if timers_dict["reader-connected-since"] is None:
                    __status_dict["reader-connected-since"] = None
                else:
                    __status_dict["reader-connected-since"] = strftime("%d.%m.%Y %H:%M:%S" + log_time_zone_str, gmtime(timers_dict["reader-connected-since"] + (log_time_zone * 3600)))
                # Time since the disconnection of reader, not empty if now disconnected
                if timers_dict["reader-disconnected-since"] is None:
                    __status_dict["reader-disconnected-since"] = None
                else:
                    __status_dict["reader-disconnected-since"] = strftime("%d.%m.%Y %H:%M:%S" + log_time_zone_str, gmtime(timers_dict["reader-disconnected-since"] + (log_time_zone * 3600)))
                # Time since last time frames received from the reader, and how many seconds ago it happened
                if timers_dict["reader-last-act-time"] is None:
                    __status_dict["reader-last-act-time"] = None
                    __status_dict["time-since-reader-last-act"] = None
                else:
                    __status_dict["reader-last-act-time"] = strftime("%d.%m.%Y %H:%M:%S" + log_time_zone_str, gmtime(timers_dict["reader-last-act-time"] + (log_time_zone * 3600)))
                    __status_dict["time-since-reader-last-act"] = float(time() - timers_dict["reader-last-act-time"])
                __status_dict["process-up-since"] = strftime("%d.%m.%Y %H:%M:%S" + log_time_zone_str, gmtime(timers_dict["process-up-since"] + (log_time_zone * 3600)))
                # Time since NTP clock check
                if timers_dict["time-since-clock-check"] is None:
                    __status_dict["time-since-clock-check"] = None
                else:
                    __status_dict["time-since-clock-check"] = strftime("%d.%m.%Y %H:%M:%S" + log_time_zone_str, gmtime(timers_dict["time-since-clock-check"] + (log_time_zone * 3600)))
                # Average and max time offsets for last 100 checks
                __ntp_avg = None
                __ntp_max = None
                if len(ntp_check_log) > 0:
                    __ntp_avg = float(sum(ntp_check_log) / float(len(ntp_check_log)))
                    __ntp_max = float(max(ntp_check_log))
                    __status_dict["ntp-avg"] = __ntp_avg
                    __status_dict["ntp-max"] = __ntp_max
                    del __ntp_avg, __ntp_max
                # Queues length
                __status_dict["queue-to-send-len"] = len(queue_to_send)
                __status_dict["queue-sent-len"] = len(queue_sent)
                __status_dict["decoded-frames-list-dicts-len"] = len(decoded_frames_list_dicts)
                __status_dict["fme-CLU-recv-list-len"] = len(fme_CLU_recv_list)
                __status_dict["fme-STS-recv-list-len"] = len(fme_STS_recv_list)
                # Current config
                __status_dict["config"] = cfg
                # Command template reference
                __status_dict["cmd-template-reference-list"] = list(cmd_ref_dict.keys())
                # Here we're writing status to message back to API
                msg_content_to_send["reply-content"]["result"] = __status_dict
            # === cleandata === clean the tag_buf
            elif fme_STS_recv_list_item[0]["query-content"]["api-method"] == "cleandata":
                __tag_buf_len = len(tag_buf)
                tag_buf = list()
                msg_content_to_send["reply-content"] = {"is-ok": True, "result": "Successfully erased " + repr(__tag_buf_len) + " RFID tag records in tag buffer"}
                log.log("Successfully erased " + repr(__tag_buf_len) + " RFID tag records in tag buffer")
            # === getdatacount === reply with the length of the tag_buf
            elif fme_STS_recv_list_item[0]["query-content"]["api-method"] == "getdatacount":
                msg_content_to_send["reply-content"] = {"is-ok": True, "result": len(tag_buf)}
            # === getdata === reply with the contents of tag_buf - give all tags to API
            elif fme_STS_recv_list_item[0]["query-content"]["api-method"] == "getdata":
                msg_content_to_send["reply-content"] = {"is-ok": True, "result": tag_buf}
            # Here sending the reply to web API
            if fme_msg.snd(fme_STS_recv_list_item[2], "STS", msg_content_to_send) == 0:
                log.log("Replied to web API: " + repr(msg_content_to_send["reply-content"]))
            else:
                log.log("Error (" + repr(fme_msg.geterr()) + ") replying to web API: " + repr(msg_content_to_send))
            # And cleanup
            del msg_content_to_send
        except Exception as __exc_error_descr_1:
            log.log("Error (" + repr(__exc_error_descr_1) + ") processing API command from web: " + repr(fme_STS_recv_list_item))
            # Here as well sending the error reply to web API
            msg_content_to_send["reply-content"] = dict()
            msg_content_to_send["reply-content"]["is-ok"] = False
            msg_content_to_send["reply-content"]["result"] = {"result": "Error: " + repr(__exc_error_descr_1)}
            if fme_msg.snd(fme_STS_recv_list_item[2], "STS", msg_content_to_send) == 0:
                log.log("Replied to web API: " + repr(msg_content_to_send["reply-content"]))
            else:
                log.log("Error (" + repr(fme_msg.geterr()) + ") replying with error to web API: " + repr(msg_content_to_send))
    # Some cleanup
    del fme_STS_recv_list_item, fme_STS_recv_list_len

    # Here we run an NTP check with interval between checks = ntp_check_interval seconds
    try:
        if (time() - timers_dict["time-since-clock-check"]) >= ntp_check_interval:
            ntp_service_response = ntp_service.request(cfg["ntp-service-url"], version=3)
            ntp_check_log.append(abs(ntp_service_response.offset))
            __ntp_avg = None
            __ntp_max = None
            if len(ntp_check_log) > 0:
                __ntp_avg = float(sum(ntp_check_log) / float(len(ntp_check_log)))
                __ntp_max = float(max(ntp_check_log))
            if abs(ntp_service_response.offset) > cfg["max-server-time-offset"]:
                log.log('NTP check ' + cfg["ntp-service-url"] + ', got offset = ' + repr(ntp_service_response.offset) + ': WARNING : server time too far from NTP time, max = ' + repr(__ntp_max) + ', avg = ' + repr(__ntp_avg))
            else:
                log.log('NTP check ' + cfg["ntp-service-url"] + ', got offset = ' + repr(ntp_service_response.offset) + ': OK, max = ' + repr(__ntp_max) + ', avg = ' + repr(__ntp_avg))
            del __ntp_avg, __ntp_max
            timers_dict["time-since-clock-check"] = time()
            if len(ntp_check_log) >= 100:
                ntp_check_log.pop(0)
    except Exception as __exc_error_descr:
        log.log("Error checking clock via NTP service: " + repr(__exc_error_descr))

    # Here is place to shutdown the process if got the flag - in the far end of the cycle
    if session_state.global_shutdown_flag:
        if fme_STS_recv_list:
            log.log("Due to shutdown received skipped API requests: " + repr(fme_STS_recv_list))
            try:
                srv_basic_sock.shutdown(SHUT_RDWR)
                srv_basic_sock.close()
                del srv_basic_sock
                rid_sock.shutdown(SHUT_RDWR)
                rid_sock.close()
                del rid_sock
            except Exception:
                pass
        log.log("Safely shutting down the process...")
        exit()
