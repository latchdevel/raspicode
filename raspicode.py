#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple RESTful API for Raspberry Pi using Flask Web Server 
to transmit picode string format RF 315/433 Mhz OOK codes 

Send OOK pulse train to digital gpio using WiringPi library
via Python C Extension Module "wiringpiook"

See: https://github.com/latchdevel/raspicode

Copyright (c) 2022 Jorge Rivera. All right reserved.
License GNU Lesser General Public License v3.0.
"""

import os               # Get environment vars and manage files
import sys              # Call sys.exit()
import time             # Time manage functions
import signal           # Catch SIGTERM signal
import socket           # Trick to get local ip
import logging          # Manage class logging
import hashlib          # Make md5 checksum of script file itself
import urllib.parse     # Parse unquote url encoding
import traceback        # Catch exception trace
                        # Flask web server instance "werkzeug"
from flask              import Flask, request, jsonify, send_from_directory

from picode import *    # Python native functions to picode string parse and convert to pulse list

try:
    import wiringpiook  # Python C Extension Module WiringPI OOK, build: "python3 setup.py develop --user"
except:
    raise("Must build wiringpiook module.")

# --------------------------------------------------------------------------- #
# Configuration

config = {
    'listen_ip'      : '0.0.0.0',           # IP address to bind server (0.0.0.0 for no IP binding)
    'listen_port'    : '8087',              # TCP listen port
    'logs_dir'       : 'logs',              # Logs directory from script path
    'log_name'       : 'web_internal.log',  # Internal log file name
    'tx_gpio'        : 18                   # Native Broadcom GPIO number (BCM SOC channel) for TX
}

# --------------------------------------------------------------------------- #
# Flask Web Server app instance

app = Flask(__name__)
app.url_map.strict_slashes = False                  # Disable strict "/" slash manage
app.config['ENV'] = "Testing"                       # Prevent warning in production without WSGI interface
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True    # jsonify responses will be output with newlines, spaces, and indentation

# Add custom response class to change default content-type header to 'text/plain'
# https://blog.miguelgrinberg.com/post/customizing-the-flask-response-class
class CustomResponse(app.response_class):

    charset = 'utf-8'
    default_status = 200
    default_mimetype = 'text/plain'

    def __init__(self, *args, **kwargs):
        super(CustomResponse, self).__init__(*args, **kwargs)
        #self.set_cookie("last-visit", time.ctime())

# Set custom response class
app.response_class = CustomResponse  

# --------------------------------------------------------------------------- #
# Logging config

script_name = os.path.basename(__file__)  # script name
script_path = os.path.abspath(__file__)   # full script path
script_dir = os.path.dirname(script_path) # script directory

logs_dir = script_dir + "/" + config['logs_dir'] + "/"
file_log = logs_dir + config['log_name']

digest = hashlib.md5(open(script_path,'rb').read()).hexdigest()

config["digest"]=digest

if not os.path.exists(logs_dir):
    try:
        os.makedirs(logs_dir)
    except:
        sys.exit("Unable to create logs directory: %s" %(logs_dir))
else:
    if not os.path.isdir(logs_dir):
        sys.exit("Not is dir logs directory: %s" %(logs_dir))

if not os.access(logs_dir, os.W_OK):
    sys.exit("Unable to write on logs directory: %s" %(logs_dir))

# Set internal web server log file
logging.basicConfig(filename=file_log, filemode='a', format='[%(asctime)s] %(process)s %(levelname)s - %(message)s') # log to file
#logging.basicConfig(format='[%(asctime)s] %(process)s %(levelname)s - %(message)s') # log to console

# Flask web server log level set to error only
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Disable Flask server console messages
logging.getLogger('werkzeug').disabled = True

# Disable startup banner log
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda * x: None

# Internal log level set to WARNING for PRODUCTION
app.logger.setLevel(logging.WARNING)

# --------------------------------------------------------------------------- #
# Logger helper

def logger(message="",levelname="INFO"):
    
    file_date = time.strftime("web_%Y_%b",time.localtime())
    file_name = logs_dir + file_date.lower() + ".log"

    process = str(os.getpid())

    timestamp = time.time() 

    mlsec = repr(timestamp).split('.')[1][:3]
    asctime = time.strftime("%Y-%m-%d %H:%M:%S,{}".format(mlsec),time.localtime(timestamp))

    try:
        file = open(file_name,"a")
        try:
            file.write("[%s] %s %s - %s \n" %(asctime,process,levelname,message))  # logging to file
            print("[%s] %s %s - %s " %(asctime,process,levelname,message))         # logging to console
        except:
            print ("Error: unable to write on file %s" %(file_name))
            app.logger.error("Error: unable to write on file %s" %(file_name))
    except:
        print ("Error: unable to open file %s" %(file_name))
        app.logger.error("Error: unable to open file %s" %(file_name)) 

    file.close()

    return

#----------------------------------------
# Gives a human-readable timedelta string

def diff_time(_time=0):
    string = ""
    if _time > 0:

        total_seconds = time.time()-_time

        MINUTE = 60
        HOUR   = MINUTE * 60
        DAY    = HOUR * 24

        # Get the days, hours, etc:
        days    = int( total_seconds   / DAY )
        hours   = int( ( total_seconds % DAY )   / HOUR )
        minutes = int( ( total_seconds % HOUR )  / MINUTE )
        seconds = int( total_seconds   % MINUTE )

        # Build up the pretty string (like this: "N days, N hours, N minutes, N seconds")
        if days > 0:
            string += str(days) + " " + (days == 1 and "day" or "days" ) + ", "
        if len(string) > 0 or hours > 0:
            string += str(hours) + " " + (hours == 1 and "hour" or "hours" ) + ", "
        if len(string) > 0 or minutes > 0:
            string += str(minutes) + " " + (minutes == 1 and "minute" or "minutes" ) + ", "
        string += str(seconds) + " " + (seconds == 1 and "second" or "seconds" )

    return string

# --------------------------------------------------------------------------- #
# Status info

status = dict()

status["logs_directory"] = logs_dir
status["script_path"] = script_path
status["script_MD5"] = digest
status["proccess_pid"] = os.getpid()
status["start_time"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
status["tx_count"] = 0
status["last_tx"] = "never"

# --------------------------------------------------------------------------- #
# Transmit picode
def tx_picode(picode=""):

    picode_dict = picode_parse(picode)

    if not picode_dict:
        return ("Error(422) Unprocessable Entity picode string parse",422)

    pulse_list = picode_pulselist(picode_dict)

    if not pulse_list:
        return ("Error(422) Unprocessable Entity picode pulse list",422)

    timed = 0
    repeats = DEFAULT_REPEATS

    if "t" in picode_dict.keys():
        timed = picode_dict["t"]
    elif "r" in picode_dict.keys():
        repeats = picode_dict["r"]

    if timed > 0:
        # Begin RF TX (timed)
        initial = time.time_ns()
        final = initial + timed*(10**9)

        while time.time_ns() < final:
            try:
                result = wiringpiook.tx(config['tx_gpio'],pulse_list,repeats)
            except Exception as err:
                return ("Error(424) %s" % err,424)
            if result < 0:
                return ("ERROR (%d)" % result,424)

        status["tx_count"] += 1
        status["last_tx"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
        
        return ("RF TX sent picode for %d secs OK" % (timed) ,202)

    else:
        # Begin RF TX (repeats)
        try:
            result = wiringpiook.tx(config['tx_gpio'],pulse_list,repeats)
        except Exception as err:
            return ("Error(424) %s" % err,424)

        if result < 0:
            return ("ERROR (%d)" % result,424)

        if result > MAX_TX_TIME:
            dropped = "TX dropped!"
        else:
            dropped = "OK"

        status["tx_count"] += 1
        status["last_tx"] = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())

        return ("RF TX sent picode in %d ms %s" % (result,dropped) ,202)

# --------------------------------------------------------------------------- #
# Route to landing page

@app.route('/', methods=['GET','POST']) 
def index():
    
    if request.method == 'GET':
        response = send_from_directory('.', "index.html", mimetype='text/html')
        response.direct_passthrough = False
        return response
    else:
        # Accept post method to prevent blocked access cross-origin frame from landing page
        return picode_post()

# --------------------------------------------------------------------------- #
# Route for favicon.ico

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    response = send_from_directory('.','favicon.ico', mimetype='image/vnd.microsoft.icon')
    response.direct_passthrough = False
    return response

# --------------------------------------------------------------------------- #
# Route to transmit picode from GET or POST request to /picode

@app.route('/picode', methods=['GET','POST'])
def picode_post():

    picode = ""

    if request.method == 'GET':
        picode = request.args.get('picode')
        if not isinstance(picode,str):
            picode = ""
        else:
            picode.strip()
    else:
        if "picode" in request.form:
            picode = request.form["picode"].strip()

    if len(picode)>0:
        return tx_picode(picode)
    else:
        return ("Error(400) Bad Request: no picode data",400)

# --------------------------------------------------------------------------- #
# Route to transmit picode from GET request to /picode/<string:picode>

@app.route('/picode/<string:picode>', methods=['GET'])
def picode_get(picode=""):

    if len(picode)>0: 
        return tx_picode(picode)
    else:
        return ("Error(400) Bad Request: no picode",400)

 
# --------------------------------------------------------------------------- #
# Show config

@app.route('/config', methods=['GET']) 
def get_config():
    return jsonify(config)

# --------------------------------------------------------------------------- #
# Show status

@app.route('/status', methods=['GET']) 
def get_status():
    status["uptime"] = diff_time(time.mktime(time.strptime(status["start_time"],"%Y-%m-%d %H:%M:%S")))
    return jsonify(status)

# --------------------------------------------------------------------------- #
# Route to show files on directory logs

@app.route('/logs')
def get_logs():

    _logs_dir = logs_dir
    _time = time.strftime("[%Y-%m-%d %H:%M:%S]",time.localtime())
    request_host = request.host 

    raw_files = os.listdir(_logs_dir)

    raw_files.sort(reverse=True, key=lambda x: os.path.getmtime(_logs_dir+x))

    file_template=""

    for file_name in raw_files:
        file = _logs_dir + file_name
        
        if (os.path.isfile(file)):
            stamp = os.stat(file).st_mtime # time of last modification
            size =  '{:>8}'.format(str(os.stat(file).st_size))  # total size, in bytes 
            str_time = '{:>22}'.format(time.strftime("%-d %b %Y %H:%M:%S",time.localtime(stamp))).lower()

            file_template +=  ("    File size %(size)s bytes %(str_time)s  <a href='http://%(request_host)s/logs/%(file_name)s'>%(file_name)s</a>\n" % locals())

    # Head template
    head_template="""
    <!DOCTYPE html>
    <head>
        <meta charset="UTF-8">
        <link rel="shortcut icon" href="/favicon.ico" type="image/x-icon" />
        <title>Raspicode logs</title>
        <script>
            window.addEventListener( "pageshow", function ( event ) {
                var historyTraversal = event.persisted || ( typeof window.performance != "undefined" && window.performance.navigation.type === 2 );
                if ( historyTraversal ) {
                    // Handle page restore.
                    window.location.reload();
                }
            });
        </script>
    </head>
    <body>
    <pre>
     
    Raspicode log files at directory: %(_logs_dir)s
    <br>"""

    # Footer template
    end_template="""
    %(_time)s <a href="#" onClick="window.location.reload();return false;">Reload</a>
    </pre>
    </body>
    </html>
    """
    return ((head_template + file_template + end_template) % locals(), {"content-type":"text/html"})

# --------------------------------------------------------------------------- #
# Route to show log file

@app.route('/logs/<string:file_to_send>')
def send_file(file_to_send=""):

    if len(file_to_send)>0:
        try:
            data = open(logs_dir+file_to_send).read()  
        except IOError as exc:
            return ("Error(404) file error %s" %(exc),404)
    else:
        return ("Error(400) file name missing",400) 

    return CustomResponse(data)

# --------------------------------------------------------------------------- #
# Custom error log for Not Found http_status_code 404

@app.errorhandler(404)
def not_found(error):
    return ("Error(404): Route not found %s" %(request.url),404)

# --------------------------------------------------------------------------- #
# Custom error log for Method Not Allowed http_status_code 405

@app.errorhandler(405)
def not_found(error):
    return ("Error(405) Method (%s) Not Allowed: The method is not allowed for the requested URL: %s" %(request.method,request.url),405)

# --------------------------------------------------------------------------- #
# Custom error log for Internal Server Error http_status_code 500 on any exception

@app.errorhandler(Exception)
def exceptions(e):
    tb = traceback.format_exc()                                               # Catch exception trace
    response = app.make_response("Internal Server Error:\n\n%s" % tb)         # Make a custom response to show exception trace
    app.logger.error("Internal Server Error: %s" %(tb))                       # Logging to internal log file
    logger( "Internal Server Error: see %s" % (file_log), "ERROR")            # Logging to web server log file
    return(response,500)  

# --------------------------------------------------------------------------- #
# Log after request to put response status

@app.after_request                        
def after_request(response):
    """ Logging after every request. """

    if response.status_code == 202 or response.status_code == 424:
        r_log = response.data.decode()
    else:
        r_log =  "sent %i bytes" %(response.content_length+1)

    if response.status_code == 200 or response.status_code == 202:
        response.status_code = 200
        log_level = "INFO"
    else:
        log_level = "ERROR"

    logger('%s %s %s %s %s' %(
            request.remote_addr,
            request.method,
            urllib.parse.unquote(request.url),
            response.status,
            r_log),log_level) 
    
    response.headers["Connection"]    = "close"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # max-age=0 # https://www.dokry.com/4244
    response.headers["Pragma"]        = "no-cache" # HTTP/1.0 compatibility
    response.headers["Expires"]       = "0"        # http://cristian.sulea.net/blog/disable-browser-caching-with-meta-html-tags/   

    response.data += b"\n"

    return response

# --------------------------------------------------------------------------- #
# Signals handler

def receiveSignalKill(signalNumber, frame):
    #https://stackabuse.com/handling-unix-signals-in-python/
    raise SystemExit()

# Catch SIGTERM signal
signal.signal(signal.SIGTERM, receiveSignalKill)

# Get local IP address
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = str(s.getsockname()[0])
    s.close()
except:
    local_ip = str("127.0.0.1")

# --------------------------------------------------------------------------- #
# Check for OS scheduler isolated cpu process affinity

status["isolated_cpu_affinity"] = "not OS scheduler isolated"

if "sched_getaffinity" in dir(os) and "sched_setaffinity" in dir(os):
    pid = os.getpid()
    os_affinity = os.sched_getaffinity(1)
    pid_affinity = os.sched_getaffinity(pid)

    if not pid_affinity.issubset(os_affinity):
        logger("Process id: %d affinity cpu: {%s} isolated from OS scheduler cpu: {%s}" % (pid,str(pid_affinity)[1:-1],str(os_affinity)[1:-1]))
        status["isolated_cpu_affinity"] = "{%s}" % str(pid_affinity)[1:-1]
    else:
        logger("Process id: %d not OS scheduler isolated cpu process affinity" %(pid), "WARINING")
        if len(os_affinity) == os.cpu_count():
            logger("Unable to isolate process because OS scheduler affinity to all cpus","WARINING")
            logger("To solve, isolate one cpu from OS scheduler adding isolcpus=n to boot params (/boot/cmdline.txt)","WARINING")
        else:
            total_cpus = set(range(0,os.cpu_count()))
            affinity_mask = total_cpus - os_affinity
            logger("Trying to set process affinity cpu: {%s}" % (str(affinity_mask)[1:-1]),"WARINING")
            try:
                os.sched_setaffinity(pid, affinity_mask)
                pid_affinity = os.sched_getaffinity(pid)
                if not pid_affinity.issubset(os_affinity):
                    logger("OK Process id: %d affinity cpu: {%s} isolated from OS scheduler cpu: {%s}" % (pid,str(pid_affinity)[1:-1],str(os_affinity)[1:-1]))
                    status["isolated_cpu_affinity"] = "{%s}" % str(pid_affinity)[1:-1]
                else:
                    logger("Unable to isolate process","ERROR")
            except:
                logger("Unable to set process affinity","ERROR")
else:
    logger("Unable to manage process affinity","WARINING")
    status["isolated_cpu_affinity"] = "unknow"

# --------------------------------------------------------------------------- #
# Main

if __name__ == "__main__":

    logger("Web server binding to %s port %s local url http://%s:%s/" %(config['listen_ip'], config['listen_port'], local_ip, config['listen_port'] ))
    logger("Directory for logs: %s" %(logs_dir)) 
    logger("File: %s Digest: 0x%s" %(script_name,digest))
    logger("TX BCM GPIO: %s" % config['tx_gpio'])

    try:
        logger("Web server start!")
        app.run(host=config['listen_ip'], port=config['listen_port'], threaded=True, debug=False)
    except (KeyboardInterrupt):
        logger("Received Control-C: Stopping Web server...")
    except (SystemExit):
        logger("Received SIGTERM: Stopping Web server...")
    except Exception as error:
        app.logger.error("error: %s" %(error))
        logger("error: %s" %(error), "ERROR")

logger("Web server stopped.")
