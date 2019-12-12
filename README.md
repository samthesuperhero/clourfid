# clourfid
A Python set of modules and apps to connect to Clou (Hopeland) RFID readers via Internet

Information about the vendor: [Hopeland](https://www.hopelandrfid.com/).

This package is to use with RFID scanning [devices](https://www.hopelandrfid.com/products/) supporting the TCP/IP connection.

Python version: **3.7**, 3.8 not tested.

Dependencies: **no**, using only Python standard library.

**The running package contains:**

|File|What is it|
|-|-|
|cloucon.py|Connector process, run in detached mode, 1 process strictly per 1 RFID device|
|clouweb.py|WSGI application, this is the web API server code, processes the API, designed to be a WSGI application behind the web server|
|clou.conf|Single config for all processes, connectors and API processors, JSON formatted|
|fme.py|Module, not to be run standalone, file messaging between connectors and WSGI apps|
|clouprotocol.py|Module, not to be run standalone, definitions and classes describing the Clou protocol|
|cloulog.py|Module, not to be run standalone, used for logging|
|[cmdref](https://github.com/samthesuperhero/clourfid/tree/master/cmdref/)|Folder with command references JSON files|

**How to deploy:**

1. Developed for linux environments, so recommended to use linux machine(s) for running the solution; please create the [issue](https://github.com/samthesuperhero/clourfid/issues/) if you'd like to run on Windows

2. First setup your Hopeland RFID scanning devices: if you set them in client mode (preferred), 
configure as destination IP the address of linux machine you will use for running connectors, but for each device set the different destination port

3. Copy the package files to the source folder on your machine

4. Create the run directory for temp files, and the log directory for logging

5. Create the **clou.conf** reflecting your setup and put it somewhere, see docs; you will need to spoecify all your RFID devices ID and required parameters in this **clou.conf** file 

6. Configure your web server; tested with Nginx

7. Configure your web server to call **clouweb.py** as WSGI app, tested with Nginx Unit

8. Ready to run **cloucon.py** processes, 1 process strictly for 1 RFID device, for example:
```
python37 /usr/share/dev/clouweb/cloucon.py msk_cl7206b2 /usr/share/dev/clouweb/clou.conf +0300 &
```

That's it. Should work! :)

If not - please, create the [issue](https://github.com/samthesuperhero/clourfid/issues/)!

Documentation:

- How to configure [clou.conf](https://github.com/samthesuperhero/clourfid/blob/master/clou.conf.txt)

- [API](https://github.com/samthesuperhero/clourfid/blob/master/Clou-RFID-reader-API-pub-v-1.pdf) to request the API through the web server

- [Read](https://github.com/samthesuperhero/clourfid/blob/master/cmdref/OP_READ_EPC_TAG.json.txt) command reference

- [Stop](https://github.com/samthesuperhero/clourfid/blob/master/cmdref/OP_STOP.json.txt) command reference
