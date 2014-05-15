import json


# http://stackoverflow.com/questions/1458450/python-serializable-objects-json    
# See also YAML    
class CpEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, CpRfMsg):
            return super(CpEncoder, self).default(obj)
        
        return obj.__dict__


# 43 Byte message structure
#class AppMessage():
#class AppMessage(object, data):
class CpRfMsg():
    def __init__(self, data):
        self.messageType = ord(data[0])
        self.nodeType = ord(data[1])
        self.extAddr = (ord(data[2])) + (ord(data[3])<<8) + (ord(data[4])<<16) + (ord(data[5])<<24) + (ord(data[6])<<32) + (ord(data[7])<<40) + (ord(data[8])<<48) + (ord(data[9])<<56)
        self.shortAddr = (ord(data[10])) + (ord(data[11])<<8)
        self.softVersion = (ord(data[12])) + (ord(data[13])<<8) + (ord(data[14])<<16) + (ord(data[15])<<24)
        self.channelMask = (ord(data[16])) + (ord(data[17])<<8) + (ord(data[18])<<16) + (ord(data[19])<<24)
        self.panId = (ord(data[20])) + (ord(data[21])<<8)
        self.workingChannel = ord(data[22])
        self.parentShortAddr = (ord(data[23])) + (ord(data[24])<<8)
        self.lqi = ord(data[25])
        self.rssi = ord(data[26])
        self.type = ord(data[27])
        self.size = ord(data[28])
        self.battery = (ord(data[29])) + (ord(data[30])<<8) + (ord(data[31])<<16) + (ord(data[32])<<24)
        self.temperature = (ord(data[33])) + (ord(data[34])<<8) + (ord(data[35])<<16) + (ord(data[36])<<24)
        self.light = (ord(data[37])) + (ord(data[38])<<8) + (ord(data[39])<<16) + (ord(data[40])<<24)
        
       
    def toJson(self):
        packet = json.dumps(self, cls=CpEncoder)
        return packet
        
        '''
        self.messageType = 0
        self.nodeType = 0
        self.shortAddr = 0
        self.softVersion = 0
        self.channelMask = 0
        self.panId = 0
        self.workingChannel = 0
        self.parentShortAddr = 0
        self.lqi = 0
        self.rssi = 0
        self.type = 0
        self.size = 0
        self.battery = 0
        self.temperature = 0
        self.light = 0
        self.cs = 0
        self.hydrate(data)
        '''
        #self.hydrate(self.data)
    '''
    def hydrate(self, data):
        msg = AppMessage()
        msg.messageType = ord(data[0])
        msg.nodeType = ord(data[1])
        msg.extAddr = (ord(data[2])) + (ord(data[3])<<8) + (ord(data[4])<<16) + (ord(data[5])<<24) + (ord(data[6])<<32) + (ord(data[7])<<40) + (ord(data[8])<<48) + (ord(data[9])<<56)
        msg.shortAddr = (ord(data[10])) + (ord(data[11])<<8)
        msg.softVersion = (ord(data[12])) + (ord(data[13])<<8) + (ord(data[14])<<16) + (ord(data[15])<<24)
        msg.channelMask = (ord(data[16])) + (ord(data[17])<<8) + (ord(data[18])<<16) + (ord(data[19])<<24)
        msg.panId = (ord(data[20])) + (ord(data[21])<<8)
        msg.workingChannel = ord(data[22])
        msg.parentShortAddr = (ord(data[23])) + (ord(data[24])<<8)
        msg.lqi = ord(data[25])
        msg.rssi = ord(data[26])
        msg.type = ord(data[27])
        msg.size = ord(data[28])
        msg.battery = (ord(data[29])) + (ord(data[30])<<8) + (ord(data[31])<<16) + (ord(data[32])<<24)
        msg.temperature = (ord(data[33])) + (ord(data[34])<<8) + (ord(data[35])<<16) + (ord(data[36])<<24)
        msg.light = (ord(data[37])) + (ord(data[38])<<8) + (ord(data[39])<<16) + (ord(data[40])<<24)
        return msg
    '''