import threading
import time
import Queue
import json
import cpcobs
import cpdb
import binascii
from datetime import datetime
from cpdb import CpDb
from cpdb import CpDbManager
from cprfmsg import CpRfMsgHeader
from cprfmsg import CpRfMsg
from cprfmsg import CpEncoder
from cpdefs import CpSystemState
from cpdefs import CpDefs
    




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

    def __init__(self, rfThread, inetThread, dbThread, ledThread, *args):
        self._target = self.task_handler
        self._args = args
        self.__lock = threading.Lock()
        self.messages = Queue.Queue(10)
        self.closing = False # A flag to indicate thread shutdown
        self.rfThread = rfThread
        self.ledThread = ledThread
        self.inetThread = inetThread
        self.inetThread.setStateChangedCallback(self.stateChangedCallback)
        self.dbThread = dbThread
        self.dctMessages = {}
        threading.Thread.__init__(self)
    
    def stateChangedCallback(self, state): 
        if(state == CpSystemState.WAITNETWORKINTERFACE):
            self.ledThread.startup()
        elif(state == CpSystemState.CONNECT):
            self.ledThread.connecting()
        elif(state == CpSystemState.IDLE):
            self.ledThread.idle()
        elif(state == CpSystemState.SEND):
            self.ledThread.sending()
        elif(state == CpSystemState.SLEEP):
            self.ledThread.sleep()
        
            
    def run(self):
        self._target(*self._args)
        
    def task_handler(self):
        # Toggle led startup pattern
        self.ledThread.startup()
        
        while not self.closing:
            # Process new messages
            self.handler_rfqueue()
            time.sleep(.0005)
        
       
    def handler_rfqueue(self):
        
        rf_encoded = self.rfThread.queue_get()
        
        # TODO: Sanity check (Redundant: checked in cprf.py)
        if(len(rf_encoded) >= CpDefs.RfMsgLen):
            
            # Decode cobs encoding
            rf_decoded = cpcobs.decode(rf_encoded)
            
            # Validate checksum
            if (checksumValid(rf_decoded) == False):
                print 'Invalid Checksum'
                return
            
            print 'Queued Message Received!!!'
            
            #self.handleNetworkThrottlingMacAddress(rf_decoded)
            self.handleNetworkThrottlingCompositeAddress(rf_decoded)
            
    
    # Throttle network traffic based upon the tag's extAddr (Mac Address)
    # This keeps messages from constantly being reported to the server
    def handleNetworkThrottlingMacAddress(self, rf_decoded):
        
            # NEW CODE TO THROTTLE NETWORK TRAFFIC
            
            # We just need to load the header to store in the dictionary
            # this will cut down on the amount of memory used when searching
            # for tags
            msg = CpRfMsgHeader(rf_decoded)
            
            if(msg.extAddr in self.dctMessages):
                # We found the mac address in the dictionary
                if((datetime.now() - self.dctMessages[msg.extAddr].timestamp).seconds >= CpDefs.RfMsgThrottleTimeout):
                    # Update the timestamp for the message in the dictionary
                    self.dctMessages[msg.extAddr].timestamp = datetime.now()
                    self.dbThread.enqueue_record(rf_decoded)
                    print 'SENDING MESSAGE AFTER TIMEOUT'
                    
            else:
                print 'NEW MESSAGE RECEIVED'
                # Add the new message to the dictionary
                self.dctMessages[msg.extAddr] = msg
                # Enqueue the message for sending
                self.dbThread.enqueue_record(rf_decoded)
                
            # END NEW CODE TO THROTTLE NETWORK TRAFFIC
            
    # Throttle network traffic based upon a composite key defined by extAddr  and routerAddr
    # This allows tag messages that have been reported via different router end points to 
    # bypass the RfMsgThrottleTimeout and be sent to the server
    def handleNetworkThrottlingCompositeAddress(self, rf_decoded):
        
            # NEW CODE TO THROTTLE NETWORK TRAFFIC
            
            # We just need to load the header to store in the dictionary
            # this will cut down on the amount of memory used when searching
            # for tags
            msg = CpRfMsgHeader(rf_decoded)
            
            # Check for Composite Address (extAddr + routerAddr)
            if(msg.compAddress in self.dctMessages):
                # We found the mac address in the dictionary
                if((datetime.now() - self.dctMessages[msg.compAddress].timestamp).seconds >= CpDefs.RfMsgThrottleTimeout):
                    # Update the timestamp for the message in the dictionary
                    self.dctMessages[msg.compAddress].timestamp = datetime.now()
                    self.dbThread.enqueue_record(rf_decoded)
                    print 'SENDING MESSAGE AFTER TIMEOUT'
                    
            else:
                print 'NEW MESSAGE RECEIVED'
                # Add the new message to the dictionary
                self.dctMessages[msg.compAddress] = msg
                # Enqueue the message for sending
                self.dbThread.enqueue_record(rf_decoded)
                
            # END NEW CODE TO THROTTLE NETWORK TRAFFIC
                
        
    def getRfThread(self):
        return self.rfThread
    
    def getDbThread(self):
        return self.dbThread
    
    def getInetThread(self):
        return self.inetThread
    
    def getLedThread(self):
        return self.ledThread
       
    def enqueue_message(self, cmd):
        try:
            self.messages.put(cmd, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "CpTaskManager messages queue is full"
            self.__lock.release()
            
    def shutdown_thread(self):
        print 'shutting down CpTaskManager...'
        self.__lock.acquire()
        self.closing = True
        self.__lock.release()