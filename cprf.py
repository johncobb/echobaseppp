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
        self.ser = serial.Serial(CpDefs.RfPort, baudrate=CpDefs.RfBaudrate, parity='N', stopbits=1, bytesize=8, xonxoff=0, rtscts=0)
        threading.Thread.__init__(self)
        
        # Note modem_set_autoctctx can be tricky when trying to call activate context
        # Activate context will throw an error if modem_set_activatecontext is called manually
        '''
        self.fmap = {0:self.modem_set_interface,
                     1:self.modem_set_msg_format,
                     2:self.modem_set_band,
                     3:self.modem_set_context,
                     4:self.modem_set_user_id,
                     5:self.modem_set_password,
                     6:self.modem_set_skipescape,
                     7:self.modem_set_socket_config,
                     8:self.modem_set_autoactctx,
                     9:0}
        '''
        
    def run(self):
        self._target(*self._args)
        
    def shutdown_thread(self):
        print 'shutting down CpRf...'
        self.__lock.acquire()
        self.closing = True
        self.__lock.release()
        if(self.ser.isOpen()):
            self.ser.close()
    
    def rf_send(self, cmd):
        print 'sending rf command ', cmd
        #self.__lock.acquire()
        #self.ser.write(cmd + '\r')
        self.ser.write(cmd)
        #self.__lock.release()
    
    first_zero_found = False
    
    
    def rf_handler(self):
        tmp_buffer = ""
        
        if(self.ser.isOpen()):
            self.ser.close()
        
        self.ser.open()
        
        while not self.closing:
            
            if (self.commands.qsize() > 0):
                rf_command = self.commands.get(True)
                self.commands.task_done()
                self.rf_send(rf_command)
                continue
            
            #if(self.ser.outWaiting() > 0):
                #print 'modem.outWaiting=', self.ser.outWaiting()
            
            #self.__lock.acquire()
            while(self.ser.inWaiting() > 0):
                #print 'rf has data!!!'
                tmp_char = self.ser.read(1)
                #print tmp_char.encode('hex')
                #if(tmp_char == '\r'):
                if(tmp_char.encode('hex') == '00'):
                    #self.data_buffer.put(tmp_buffer, block=True, timeout=1)
                    #result = self.rf_parse_result(tmp_buffer)
                    #print 'received ', tmp_buffer.encode('hex')
                    # Make sure we received something worth processing
                    #if(result.ResultCode > CpRfResultCode.RESULT_UNKNOWN):
                        #print 'known result code', result
                    if(self.rfResponseCallbackFunc != None):
                        #self.rfResponseCallbackFunc(result)
                        if(self.first_zero_found == True):
                            #self.data_buffer.put(tmp_buffer, block=True, timeout=1)
                            self.enqueue_rf(tmp_buffer)
                            #self.rfResponseCallbackFunc(tmp_buffer)
                            self.rfBusy = False
                        else:
                            self.first_zero_found = True
                            
                    #print 'rfresponse ', tmp_buffer
                    tmp_buffer= ""
                else:
                    tmp_buffer += tmp_char
                    #tmp_buffer += tmp_char.encode('hex')
            #self.__lock.release()
            time.sleep(.005)

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
        '''
        print 'Setting up UART1...'
        UART.setup("UART1")
        print 'Setting up UART2...'
        UART.setup("UART2")
        print 'Setting up UART4...'
        UART.setup("UART4")
        print 'Setting up UART5...'
        UART.setup("UART5")
        
    
        print 'Initializing GPIO(s)'
        
        GPIO.setup("P9_12", GPIO.OUT) #CELL_ENABLE
        GPIO.setup("P9_23", GPIO.OUT) #CELL_RESET
        GPIO.setup("P8_12", GPIO.OUT) #CELL_ONOFF
        
        GPIO.output("P9_12", GPIO.LOW)
        GPIO.output("P9_23", GPIO.LOW)
        GPIO.output("P8_12", GPIO.LOW)
        
        time.sleep(3)
        
        print 'Setting CELL_ON/OFF HIGH'
        GPIO.output("P8_12", GPIO.HIGH)
        time.sleep(5)
        print 'Wait (5)s...'
        print 'Setting CELL_ON/OFF LOW'
        GPIO.output("P8_12", GPIO.LOW)
        '''
    
    def rf_reset(self):
        
        '''
        print 'Setting CELL_ON/OFF HIGH'
        GPIO.output("P8_12", GPIO.HIGH)
        time.sleep(5)
        print 'Wait (5)s...'
        print 'Setting CELL_ON/OFF LOW'
        GPIO.output("P8_12", GPIO.LOW)
        '''

 
    def rf_send_at(self, callback):
        self.enqueue_command(CpRfDefs.CMD_AT)
        self.rfResponseCallbackFunc = callback
        pass
    
    



