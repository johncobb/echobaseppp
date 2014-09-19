import time
import sys, getopt
from cpconsole import CpConsole
from cptaskmanager import CpTaskManager
from cprf import CpRf
#from cpinet import CpInet
from cpinet_v2 import CpInet
from cpdb import CpDb
from cpdb import CpDbManager
from cpdefs import CpDefs
from cpdefs import CpGpioMap
from cplog import CpLog
from cpled import CpLed
'''
import Adafruit_BBIO.UART as UART
import Adafruit_BBIO.GPIO as GPIO

from datetime import datetime
'''


    
def rfDataReceived(data):
    #print 'Callback function rfDataReceived ', data
    pass
    
def inetDataReceived(data):
    #print 'Callback function inetDataReceived ', data
    pass
    
    
def main(argv):
    
    runas = 'console'
    print "Starting thread main..."
    try:
        opts, args = getopt.getopt(argv,"hm:",["mode="])
    except getopt.GetoptError:
        print 'main.py.py -m <service>|<console>'
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-h':
            print 'main.py.py -m <service>|<console>'
            sys.exit()
        elif opt in ("-m", "--mode"):
            runas = arg.strip()
            
            start_threads(runas)
            print runas == 'server'
        else:
            start_threads(runas.strip())
            
def start_threads(runas):
    
    if runas not in ("console", "service"):
        print "Error invalid command line argument (%s)" % runas
        exit(1)
    
    print 'Echobase 1.0 starting services...'
    print 'mode=', runas
    
    #print 'Wait 30 seconds for network to startup'
    #time.sleep(30)
    print 'Done waiting...'
    rfThread = CpRf(rfDataReceived)
    rfThread.start()
    
    inetThread = CpInet(inetDataReceived)
    inetThread.start()
    
    dbThread = CpDbManager(inetThread)
    dbThread.start()
    
    ledThread = CpLed()
    ledThread.start()
    
    taskThread = CpTaskManager(rfThread, inetThread, dbThread, ledThread)
    taskThread.start()
    
    if(runas == 'service'):
        while(taskThread.isAlive()):
            time.sleep(.005)

            print 'Exiting App...'
            exit()
    else:
        consoleThread = CpConsole(taskThread)
        consoleThread.start()
    
        while(consoleThread.isAlive()):
    
            time.sleep(.005)
    
        print 'Exiting App...'
        exit()
        
        
        
      
            
if __name__ == '__main__':
    
    if CpDefs.LogToStdOut == True:
        # Route standard out to a log file
        log = CpLog()
        log.logStdOut()
    
    print "one"
    print "two"
    print "three"
    main(sys.argv[1:])
    

    '''
    rfThread = CpRf(rfDataReceived)
    rfThread.start()
    
    inetThread = CpInet(inetDataReceived)
    inetThread.start()
    
    dbThread = CpDbManager(inetThread)
    dbThread.start()
    
    taskThread = CpTaskManager(rfThread, inetThread, dbThread)
    taskThread.start()
    
    consoleThread = CpConsole(taskThread)
    consoleThread.start()
    
    while(consoleThread.isAlive()):

        time.sleep(.005)

    print 'Exiting App...'
    exit()
    '''
    
    


    
