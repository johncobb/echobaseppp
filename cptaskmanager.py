import threading
import time
import Queue
import json
import cpcobs
import cpdb
import binascii
from cpdb import CpDb
from cpdb import CpDbManager
from cprfmsg import CpRfMsg
from cprfmsg import CpEncoder
    

def dataReceived(rf_data):
    pass

def checksum(data):
    cs = 0x00
    
    sentence = data[:-1]
    print 'sentence: ', sentence.encode('hex')
    for s in sentence:
        cs ^= ord(s)
    print 'checksum', cs
    return cs
    

def checksumValid(data):
    cs = checksum(data)
    return (ord(data[len(data)-1]) == cs)
    
class CpTaskManager(threading.Thread):

    def __init__(self, rfThread, inetThread, dbThread, *args):
        self._target = self.task_handler
        self._args = args
        self.__lock = threading.Lock()
        self.messages = Queue.Queue(10)
        self.closing = False # A flag to indicate thread shutdown
        self.rfThread = rfThread
        self.inetThread = inetThread
        self.dbThread = dbThread
        threading.Thread.__init__(self)
        
    def run(self):
        self._target(*self._args)
        
    def task_handler(self):
        
        while not self.closing:
            # Process new messages
            self.handler_rfqueue()
            time.sleep(.0005)
        
        
    def handler_rfqueue(self):
        
        rf_encoded = self.rfThread.queue_get()
        
        # Sanity check
        if(len(rf_encoded) == 43):
            
            # Decode cobs encoding
            rf_decoded = cpcobs.decode(rf_encoded)
            
            # Validate checksum
            if (checksumValid(rf_decoded) == False):
                print 'Invalid Checksum'
                return
            
            print 'Queued Message Received!!!'
            
            self.dbThread.enqueue_record(rf_decoded)
            
            #msg = CpRfMsg(rf_decoded)
            
            #self.db.updateRecord(msg.shortAddr, binascii.hexlify(rf_data))
            #self.db.updateRecord(msg.shortAddr, binascii.hexlify(rf_decoded))
            
            
            #packet = msg.toJson()
            #self.inetThread.enqueue_packet(packet)
            #self.inetThread.enqueue_packet(msg.toJson()) 
    
    def getRfThread(self):
        return self.rfThread
    
    def getDbThread(self):
        return self.dbThread
    
    def getInetThread(self):
        return self.inetThread
       
    def enqueue_message(self, cmd):
        try:
            self.messages.put(cmd, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "The queue is full"
            self.__release()
            
    def shutdown_thread(self):
        print 'shutting down CpTaskManager...'
        self.__lock.acquire()
        self.closing = True
        self.__lock.release()