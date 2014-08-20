
import threading
import time
import Adafruit_BBIO.GPIO as GPIO

class CpGpioMap():
    GPIO_CELLENABLE = "P9_12"
    GPIO_CELLRESET = "P9_23"
    GPIO_CELLONOFF = "P8_12"
    GPIO_CELLPWRMON = "P9_42"
    GPIO_LED1 = "P8_14"
    GPIO_LED2 = "P8_15"

class CpLedState:
    LEDOFF = 0,
    LEDON = 1
    
class CpLedLight():
    def __init__(self, ledId, *args):
        self.ledState = CpLedState.LEDOFF
        self.led = ledId
    
    
    
class CpLed(threading.Thread):

    def __init__(self, *args):
        self._target = self.task_handler
        self._args = args
        self.__lock = threading.Lock()
        self.fmapIndex = 0
        self.closing = False # A flag to indicate thread shutdown
        threading.Thread.__init__(self)
        self.LED1 = CpLedLight(CpGpioMap.GPIO_LED1)
        self.LED2 = CpLedLight(CpGpioMap.GPIO_LED2)     
        self.fmap = {0:self.led_startup,
                     1:self.led_connecting,
                     2:self.led_idle,
                     3:self.led_sleep,
                     4:self.led_send,
                     5:0}           
        
        
    def run(self):
        self._target(*self._args)
        
    def task_handler(self):

        '''
        GPIO.setup(CpGpioMap.GPIO_LED1, GPIO.OUT) #LED1
        GPIO.setup(CpGpioMap.GPIO_LED2, GPIO.OUT) #LED2
        '''
        
        GPIO.setup(self.LED1.led, GPIO.OUT) #LED1
        GPIO.setup(self.LED2.led, GPIO.OUT) #LED2
        self.startup()        
        
        while not self.closing:
            self.fmap[self.fmapIndex]()
            time.sleep(.05)
    
    # Each time we enter a new led pattern we need
    # to start with the leds off
    def enter_state(self, index):
        self.fmapIndex = index
        #self.toggleLed(self.LED1, CpLedState.LEDOFF)
        #self.toggleLed(self.LED2, CpLedState.LEDOFF)
        self.LED1.ledState = CpLedState.LEDOFF
        self.LED2.ledState = CpLedState.LEDOFF
        GPIO.output(self.LED1, GPIO.LOW)
        GPIO.output(self.LED2, GPIO.LOW)
        
    def toggleLed(self, led, state):
        led.ledState = state
        if(state == CpLedState.LEDOFF):
            GPIO.output(led.led, GPIO.LOW)
        else:
            GPIO.output(led.led, GPIO.HIGH)
            
    
    def startup(self):
        self.enter_state(0)
        
    def connecting(self):
        self.enter_state(1)
        
    def idle(self):
        self.enter_state(2)
        
    def sleep(self):
        self.enter_state(3)
        
    def sending(self):
        self.enter_state(4)                      
        
    def led_startup(self):
        
        #GPIO.output(self.LED2.led, GPIO.LOW)
        
        self.toggleLed(self.LED1, CpLedState.LEDON)
        time.sleep(.5)
        self.toggleLed(self.LED1, CpLedState.LEDOFF)
        time.sleep(.5)
        
    
    def led_connecting(self): 
        self.toggleLed(self.LED1, CpLedState.LEDON)
        time.sleep(.1)
        self.toggleLed(self.LED1, CpLedState.LEDOFF)
        
        self.toggleLed(self.LED2, CpLedState.LEDON)
        time.sleep(.1)
        self.toggleLed(self.LED2, CpLedState.LEDOFF)
        
        
    def led_send(self): 
        self.toggleLed(self.LED1, CpLedState.LEDON)
        time.sleep(.05)
        self.toggleLed(self.LED1, CpLedState.LEDOFF)
        
        self.toggleLed(self.LED2, CpLedState.LEDON)
        time.sleep(.05)
        self.toggleLed(self.LED2, CpLedState.LEDOFF)          
 
 
    def led_idle(self): 
        #GPIO.output(self.LED1.led, GPIO.LOW)
        #GPIO.output(self.LED2.led, GPIO.LOW)
        
        self.toggleLed(self.LED1, CpLedState.LEDON)
        time.sleep(.25)
        self.toggleLed(self.LED1, CpLedState.LEDOFF)  
        
        self.toggleLed(self.LED2, CpLedState.LEDON)
        time.sleep(.25)
        self.toggleLed(self.LED2, CpLedState.LEDOFF)  
            
        time.sleep(1)
    
    def led_sleep(self): 
        #GPIO.output(self.LED1.led, GPIO.LOW)
        self.toggleLed(self.LED2, CpLedState.LEDON)
        time.sleep(2)
        self.toggleLed(self.LED2, CpLedState.LEDOFF)
        time.sleep(2)

    
  

            
    def shutdown_thread(self):
        print 'shutting down CpLed...'
        self.__lock.acquire()
        self.closing = True
        self.__lock.release()


        
        
if __name__ == '__main__':
    
    cpLed = CpLed()
    cpLed.start()    
    
    while(cpLed.isAlive()):
        
        input = raw_input(">> ")
        # Python 3 users
        # input = input(">> ")
        if input == 'exit' or input == 'EXIT':
            cpLed.shutdown_thread()
        elif input == '0':
            cpLed.startup()
            print 'startup'
        elif input == '1':
            cpLed.connecting()
            print 'connecting'
        elif input  == '2':
            cpLed.idle()
            print 'idle'
        elif input  == '3':
            cpLed.sleep() 
            print 'sleep'           
        elif input  == '4':
            cpLed.sending()      
            print 'sending'      
                
        time.sleep(.005)
        
    print 'Exiting App...'
    exit()
    
    
    