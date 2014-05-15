import time
import sys, getopt
from cpconsole import CpConsole
from cptaskmanager import CpTaskManager
from cprf import CpRf
from cpinet import CpInet
from cpdb import CpDb
from cpdb import CpDbManager
'''
import Adafruit_BBIO.UART as UART
import Adafruit_BBIO.GPIO as GPIO

from datetime import datetime
'''

class CpGpioMap():
    GPIO_CELLENABLE = "P9_12"
    GPIO_CELLRESET = "P9_23"
    GPIO_CELLONOFF = "P8_12"
    GPIO_CELLPWRMON = "P9_42"
    
def rfDataReceived(data):
    print 'Callback function rfDataReceived ', data
    
def inetDataReceived(data):
    print 'Callback function inetDataReceived ', data
    
    
def main(argv):
    
    runas = 'console'
    
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
    
    if runas not in ("console", "server"):
        print "Error invalid command line argument (%s)" % runas
        exit(1)
    
    print 'Echobase 1.0 starting services...'
    print 'mode=', runas
    
    
    rfThread = CpRf(rfDataReceived)
    rfThread.start()
    
    inetThread = CpInet(inetDataReceived)
    inetThread.start()
    
    dbThread = CpDbManager(inetThread)
    dbThread.start()
    
    taskThread = CpTaskManager(rfThread, inetThread, dbThread)
    taskThread.start()
    
    if(runas == 'server'):
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
    
    


    
