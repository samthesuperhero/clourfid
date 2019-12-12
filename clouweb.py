"""
Web application clouweb,
web component of RFID scanning API for Clou Hopeland
RFID readers access remotely.
This web application provides web API for users to access,
use and manage Clou Hopeland RFID scanners.

sudo curl -vv -d @./OP_STOP.json 'http://testapp.viledadev.ru/api/v1/msk_cl7206b2/query'
sudo curl -vv 'http://testapp.viledadev.ru/api/v1/msk_cl7206b2/update'
sudo curl -vv -d @./OP_READ_EPC_TAG.json 'http://testapp.viledadev.ru/api/v1/msk_cl7206b2/query'
sudo curl -vv -d '{"msid": "MAN_QUERY_INFO"}' 'http://testapp.viledadev.ru/api/v1/msk_cl7206b2/query'

"""
import os
import os.path
from json import load, loads, dumps
from time import time, sleep
from random import seed, randrange, getrandbits
import ntplib
import fme

def application(environ, start_response):
    """ Main web application """
    conf_file_name = "/usr/share/dev/clouweb/clou.conf"
    response_payload_success = bytes()
    ref_full_api_method_list = [
        "getstatus",
        "query",
        "getdatacount",
        "getdata",
        "cleandata",
        "shutdown",
        "update"
        ]

    try:
        request_method_val = environ['REQUEST_METHOD']
    except Exception as __exc_error_descr:
        response_status = "400 Bad Request"
        response_payload = bytes('{"Error": "No method read in wsgi: ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        request_path_info_val = environ['PATH_INFO']
    except Exception as __exc_error_descr:
        response_status = "400 Bad Request"
        response_payload = bytes('{"Error": "No path: ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    if request_method_val not in ["GET", "HEAD", "POST"]:
        response_status = "405 Method Not Allowed"
        response_headers = [("Allow", "GET, HEAD, POST")]
        start_response(response_status, response_headers)
        return response_payload

    try:
        request_url_split = os.path.split(request_path_info_val.strip("/"))
        request_url_split_left = request_url_split[0].strip("/")
        api_method = request_url_split[1]
        request_url_apipart = os.path.split(request_url_split_left)[0].strip("/")
        rid_value = os.path.split(request_url_split_left)[1]
    except Exception as __exc_error_descr:
        response_status = "404 Not Found"
        response_payload = bytes('{"Error": "' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    if (request_url_apipart != "api/v1") or (api_method not in ref_full_api_method_list):
        response_status = "404 Not Found"
        response_headers = list()
        start_response(response_status, response_headers)
        return bytes()

    try:
        app_config_json_file = open(conf_file_name, "r")
    except Exception as __exc_error_descr:
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Can not open config: ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        app_config_json = load(app_config_json_file)
        app_config_json_file.close()
    except Exception as __exc_error_descr:
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Bad JSON in config: ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        if not isinstance(app_config_json["max-server-time-offset"], float):
            raise Exception
        if app_config_json["ntp-service-url"] != str():
            ntp_service = ntplib.NTPClient()
            ntp_service_response = ntp_service.request(app_config_json["ntp-service-url"], version=3)
    except Exception as __exc_error_descr:
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Can not check NTP service with settings in config: ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        if abs(ntp_service_response.offset) > app_config_json["max-server-time-offset"]:
            raise Exception
    except Exception as __exc_error_descr:
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Server time too far from NTP time at ' + app_config_json["ntp-service-url"] + ', offset = ' + repr(ntp_service_response.offset) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        tmp_err_param = str()
        clou_run_dir = app_config_json["clou-run"]
        if not isinstance(clou_run_dir, str):
            tmp_err_param = "clou-run"
            raise Exception
        readers_list = app_config_json["readers-list"]
        if not isinstance(readers_list, list):
            tmp_err_param = "readers-list"
            raise Exception
        for tmp_idx_readers in readers_list:
            if tmp_idx_readers not in app_config_json.keys():
                tmp_err_param = tmp_idx_readers + " not in JSON keys"
                raise Exception
        reply_wait_timeout = app_config_json["reply-from-reader-timeout"]
        reply_read_delay = app_config_json["delay-between-reads"]
        if not isinstance(reply_wait_timeout, float):
            tmp_err_param = "reply_wait_timeout"
            raise Exception
        if not isinstance(reply_read_delay, float):
            tmp_err_param = "reply_read_delay"
            raise Exception
    except Exception as __exc_error_descr:
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Missing or wrong parameters:' + tmp_err_param + ' in config: ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    # Here we check for worker files and create own random worker ID to be different
    try:
        seed()
        worker_files_ex = list()
        if not os.access("/" + clou_run_dir.strip("/") + "/webworkers", os.F_OK):
            os.mkdir("/" + clou_run_dir.strip("/") + "/webworkers")
        for tmp_root, tmp_dirs, tmp_files in os.walk("/" + clou_run_dir.strip("/") + "/webworkers"):
            for tmp_name_walk_f in tmp_files:
                if tmp_name_walk_f.strip("/").isdigit():
                    worker_files_ex.append(int(tmp_name_walk_f))
        this_worker_id = max(worker_files_ex, default=0) + randrange(2**32)
        this_worker_id_filename = os.path.join(tmp_root, str(this_worker_id))
        tmp_file_d = open(this_worker_id_filename, "wb")
        tmp_file_d.close()
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Can not put worker file in: ' + '/' + clou_run_dir.strip('/') + '/webworkers' + ': ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        request_payload = str(environ['wsgi.input'].read().decode("utf-8"))
        if not request_payload.isascii():
            raise Exception
        request_payload_dict = dict()
        if request_payload:
            request_payload_dict = loads(request_payload)
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Wrong JSON payload in request or non-ASCII characters in JSON: ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    dir_msg_name = str("/" + clou_run_dir.strip("/") + "/" + rid_value)

    try:
        if not os.access(dir_msg_name, os.F_OK):
            os.mkdir(dir_msg_name)
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Error checking dir: ' + dir_msg_name + ': ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        fme_msg = fme.FileMessageExchange(str(this_worker_id), dir_msg_name, message_types_set=["CLU", "STS"])
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Error creating FileMessageExchange() or ClouProtocolDefinitions(): ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    # Here creating message content
    msg_content_to_send = dict()
    try:
        tmp_random_id = bytes()
        tmp_random_id += int(time()*10).to_bytes(5, 'big')
        tmp_random_id += getrandbits(11*8).to_bytes(11, 'big')
        msg_content_to_send["web-req-id"] = str().join(format(__tmp_x0, '02x') for __tmp_x0 in tmp_random_id)
        del tmp_random_id
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Error creating msg_content_to_send: ' + repr(__exc_error_descr) + '}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    # Sending query type of web request
    try:
        if api_method == "query":
            msg_content_to_send["query-content"] = request_payload_dict
            if fme_msg.snd(rid_value, "CLU", msg_content_to_send) == -1:
                msg_content_to_send = dict()
                raise Exception
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Error (' + repr(fme_msg.geterr()) + ') sending the query with snd(): ' + repr(msg_content_to_send) + ': ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        if api_method == "query":
            reply_wait_timeout_start = time()
            while True:
                if time() > (reply_wait_timeout_start + reply_wait_timeout):
                    try:
                        os.remove(this_worker_id_filename)
                    except Exception:
                        pass
                    response_status = "504 Gateway Timeout"
                    response_payload = bytes('{"Error": "Waiting time of reply from reader exceeded configured timeout = ' + repr(reply_wait_timeout) + 'sec"}', "ascii")
                    response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
                    start_response(response_status, response_headers)
                    return response_payload
                __msg_rcv_count = fme_msg.rcv(rid_value, "CLU")
                if __msg_rcv_count > 0:
                    msg_rcv_list = fme_msg.getall()
                    for msg_rcv_list_item in msg_rcv_list:
                        if msg_rcv_list_item[0]["web-req-id"] == msg_content_to_send["web-req-id"]:
                            if request_method_val != "HEAD":
                                response_payload_success = dumps(msg_rcv_list_item[0]["reply-content"], skipkeys=True).encode("ascii")
                            response_status = "200 OK"
                            response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload_success)))]
                            try:
                                os.remove(this_worker_id_filename)
                            except Exception:
                                pass
                            start_response(response_status, response_headers)
                            return response_payload_success
                    sleep(reply_read_delay)
                else:
                    sleep(reply_read_delay)
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Error at receiving reply for query method with rcv(): ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        if api_method in ["update", "shutdown", "getdata", "getdatacount", "cleandata", "getstatus"]:
            msg_content_to_send["query-content"] = {"api-method": api_method}
            if fme_msg.snd(rid_value, "STS", msg_content_to_send) == -1:
                msg_content_to_send = dict()
                raise Exception
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Error (' + repr(fme_msg.geterr()) + ') sending the query with snd(): ' + repr(msg_content_to_send) + ': ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    try:
        if api_method in ["update", "shutdown", "getdata", "getdatacount", "cleandata", "getstatus"]:
            reply_wait_timeout_start = time()
            while True:
                if time() > (reply_wait_timeout_start + reply_wait_timeout):
                    try:
                        os.remove(this_worker_id_filename)
                    except Exception:
                        pass
                    response_status = "504 Gateway Timeout"
                    response_payload = bytes('{"Error": "Waiting time of reply from reader exceeded configured timeout = ' + repr(reply_wait_timeout) + 'sec"}', "ascii")
                    response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
                    start_response(response_status, response_headers)
                    return response_payload
                __msg_rcv_count = fme_msg.rcv(rid_value, "STS")
                if __msg_rcv_count > 0:
                    msg_rcv_list = fme_msg.getall()
                    for msg_rcv_list_item in msg_rcv_list:
                        if msg_rcv_list_item[0]["web-req-id"] == msg_content_to_send["web-req-id"]:
                            if request_method_val != "HEAD":
                                response_payload_success = dumps(msg_rcv_list_item[0]["reply-content"], skipkeys=True).encode("ascii")
                            response_status = "200 OK"
                            response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload_success)))]
                            try:
                                os.remove(this_worker_id_filename)
                            except Exception:
                                pass
                            start_response(response_status, response_headers)
                            return response_payload_success
                    sleep(reply_read_delay)
                else:
                    sleep(reply_read_delay)
    except Exception as __exc_error_descr:
        try:
            os.remove(this_worker_id_filename)
        except Exception:
            pass
        response_status = "500 Internal Server Error"
        response_payload = bytes('{"Error": "Error at receiving reply for ' + repr(api_method) + ' method with rcv(): ' + repr(__exc_error_descr) + '"}', "ascii")
        response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload)))]
        start_response(response_status, response_headers)
        return response_payload

    response_status = "200 OK"
    if request_method_val == "HEAD":
        response_payload_success = bytes()
    response_headers = [("Content-type", "application/json"), ("Content-Length", str(len(response_payload_success)))]
    try:
        os.remove(this_worker_id_filename)
    except Exception:
        pass
    start_response(response_status, response_headers)
    return response_payload_success
