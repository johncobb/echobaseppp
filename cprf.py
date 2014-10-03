import threading
import time
import Queue
import serial
from cpdefs import CpDefs
from datetime import datetime
#import Adafruit_BBIO.UART as UART
#import Adafruit_BBIO.GPIO as GPIO

class CpRfResultCode:
    RESULT_UNKNOWN = 0
    RESULT_OK = 1
    RESULT_ERROR = 2
    RESULT_CONNECT = 3
    RESULT_TIMEOUT = 4
    
class CpRfResponses:
    TOKEN_OK = "OK"
    TOKEN_ERROR = "ERROR"
    TOKEN_CONNECT = "CONNECT"
    
class CpRfDefs:
    CMD_CTLZ = 0x1b
    CMD_ESC = 0x1a

class CpRfResult:
    ResultCode = 0
    Data = ""
    
class CpRf(threading.Thread):
    
    def __init__(self, rfResponseCallbackFunc=None, *args):
        self._target = self.rf_handler
        self._args = args
        self.__lock = threading.Lock()
        self.closing = False # A flag to indicate thread shutdown
        self.commands = Queue.Queue(5)
        self.data_buffer = Queue.Queue(128)
        self.modem_timeout = 0
        self.rfResponseCallbackFunc = rfResponseCallbackFunc
        self.rfBusy = False
        self.rfResult = CpRfResult()
        self.rfToken = ""
        # Used to find the first 0x00 in the byte stream
        # Once found ignore that message and continue processing
        # onto the next 0x00 found. This is our first full message
        self.first_zero_found = False
        self.ser = serial.Serial(CpDefs.RfPort, baudrate=CpDefs.RfBaudrate, parity='N', stopbits=1, bytesize=8, xonxoff=0, rtscts=0)
        threading.Thread.__init__(self)
        
    def get_queue_depth(self):
        return self.data_buffer.qsize()
      
    def run(self):
        self._target(*self._args)
        
    def shutdown_thread(self):
        print 'shutting down CpRf...'
        self.__lock.acquire()
        self.closing = True
        self.__lock.release()
        
        
        # Wait for rf_handler to stop
        # Allow approx 5 sec. before forcing close on serial
        for i in range (0, 10):
            if(self.rfBusy):
                time.sleep(.5)
            else:
                break
            
        if(self.ser.isOpen()):
            try:
                self.ser.close()
            except Exception, e:
                print "CpRf::shutdown_thread ERROR: ", e
    
    def rf_send(self, cmd):
        print 'sending rf command ', cmd
        #self.__lock.acquire()
        #self.ser.write(cmd + '\r')
        self.ser.write(cmd)
        #self.__lock.release()
    

    
    def rf_handler(self):
        tmp_buffer = ""
        
        if(self.ser.isOpen()):
            self.ser.close()
        
        self.ser.open()
        
        self.rfBusy = True
        
        while not self.closing:
            
            if (self.commands.qsize() > 0):
                rf_command = self.commands.get(True)
                self.commands.task_done()
                self.rf_send(rf_command)
                continue
            
            # While we have serial data process the buffer
            while(self.ser.inWaiting() > 0):
                # Sanity check for tight loop processing
                if(self.closing):
                    break
                
                #print 'rf has data!!!'
                tmp_char = self.ser.read(1)
                #print tmp_char.encode('hex')
                if(tmp_char.encode('hex') == '00'):
                    if(self.rfResponseCallbackFunc != None):
                        #self.rfResponseCallbackFunc(result)
                        if(self.first_zero_found == True):
                            # Sanity check on the message length
                            if(len(tmp_buffer) >= CpDefs.RfMsgLen):
                                self.enqueue_rf(tmp_buffer)
                                
                        else:
                            self.first_zero_found = True
                    # Reset tmp_buffer       
                    tmp_buffer= ""
                else:
                    tmp_buffer += tmp_char

            time.sleep(.005)
            
        self.rfBusy = False

    def enqueue_rf(self, rf):
        try:
            self.data_buffer.put(rf, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "The queue is full"
            self.__lock.release()
                        
    def queue_get(self):
        
        rf_data = "\x00"
        
        if (self.data_buffer.qsize() > 0):
            rf_data = self.data_buffer.get(True)
            self.data_buffer.task_done()
            
        return rf_data
    
    '''
    def h2b(self, hex):
        return int(hex,16)
    '''       
                    
    def enqueue_command(self, cmd):
        try:
            self.modemBusy = True
            self.commands.put(cmd, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "The Rf queue is full"
            self.__lock.release()
            
    rfTimeout = 0
    
    def set_timeout(self, timeout):
        self.rf_timeout = datetime.now() + timeout
    
    def is_timeout(self):
        if(datetime.now() >= self.rf_timeout):
            return True
        else:
            return False
    
    def is_error(self, token):        
        if(token.find(CpRfResponses.TOKEN_ERROR) > -1):
            return True
        else:
            return False
        
    def rf_parse_result(self, result):
        
        modem_result = CpRfResult()
        
        if(result.find(CpRfResponses.TOKEN_OK) > -1):
            modem_result.Data = result
            modem_result.ResultCode = CpRfResultCode.RESULT_OK
        elif(result.find(CpRfResponses.TOKEN_ERROR) > -1):
            modem_result.Data = result
            modem_result.ResultCode = CpRfResultCode.RESULT_ERROR
        elif(result.find(CpRfResponses.TOKEN_CONNECT) > -1):
            modem_result.Data = result
            modem_result.ResultCode = CpRfResultCode.RESULT_CONNECT   
        elif(result.find(CpRfResponses.TOKEN_NOCARRIER) > -1):
            modem_result.Data = result
            modem_result.ResultCode = CpRfResultCode.RESULT_NOCARRIER
        else:
            modem_result.Data = result
            modem_result.ResultCode = CpRfResultCode.RESULT_UNKNOWN
                
        return modem_result
            
    
    def rf_init(self):
        pass

    
    def rf_reset(self):
        pass

 
    def rf_send_at(self, callback):
        self.enqueue_command(CpRfDefs.CMD_AT)
        self.rfResponseCallbackFunc = callback
        pass
    
    



