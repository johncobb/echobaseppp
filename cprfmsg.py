import json
import base64
from datetime import datetime
from cpdefs import CpDefs



# http://stackoverflow.com/questions/1458450/python-serializable-objects-json    
# See also YAML    
class CpEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, CpRfMsg):
            return super(CpEncoder, self).default(obj)
        
        return obj.__dict__

# RfMsgLen Byte message structure
class CpRfMsg():
    def __init__(self, data):
        self.raw = data
        self.messageType = ord(data[0])
        self.nodeType = ord(data[1])
        self.extAddr = (ord(data[2])) + (ord(data[3])<<8) + (ord(data[4])<<16) + (ord(data[5])<<24) + (ord(data[6])<<32) + (ord(data[7])<<40) + (ord(data[8])<<48) + (ord(data[9])<<56)
        self.shortAddr = (ord(data[10])) + (ord(data[11])<<8)
        self.routerAddr = (ord(data[12])) + (ord(data[13])<<8) + (ord(data[14])<<16) + (ord(data[15])<<24) +(ord(data[16])<<32) + (ord(data[17])<<40) + (ord(data[18])<<48) + (ord(data[19])<<56)
        self.panId = (ord(data[20])) + (ord(data[21])<<8)
        self.workingChannel = ord(data[22])
        self.parentShortAddr = (ord(data[23])) + (ord(data[24])<<8)
        self.lqi = ord(data[25])
        self.rssi = ord(data[26])
        self.type = ord(data[27])
        self.size = ord(data[28])
        self.battery = (ord(data[29])) + (ord(data[30])<<8) + (ord(data[31])<<16) + (ord(data[32])<<24)
        self.temperature = (ord(data[33])) + (ord(data[34])<<8) + (ord(data[35])<<16) + (ord(data[36])<<24)
        
        #new code
        self.count = 1
        self.compAddress = self.extAddr + self.routerAddr
        self.timestamp = datetime.now()
        #/new code
        
        #self.light = (ord(data[37])) + (ord(data[38])<<8) + (ord(data[39])<<16) + (ord(data[40])<<24)
        
    def smoothRssi(self):
        #dctMessages[key].rssi = dctMessages[key].rssi/dctMessages.rssi[key].count
        self.rssi = self.rssi / self.count
        # Copy the first 25 bytes, assgin new rssi to 26th byte then copy remaining bytes
        self.raw = self.raw[:25] + chr(self.rssi) + self.raw[26:]
    
    def toJson(self):
        packet = json.dumps(self, cls=CpEncoder)
        return packet
    
    def toCustomJson(self):
        packet = "['%s']" % self.raw
        
        return packet
    
    def toCustomJsonBase64(self):
        
        encoded = base64.b64encode(self.raw)
        
        packet = "['%s']" % encoded
        
        if (CpDefs.LogEncodedMessage):
            print 'Encoded Packet'
            print packet
            print 'End Encoded Packet'
        
        return packet   
        
class CpRfMsgHeader():
    def __init__(self, data):
        self.messageType = ord(data[0])
        self.extAddr = (ord(data[2])) + (ord(data[3])<<8) + (ord(data[4])<<16) + (ord(data[5])<<24) + (ord(data[6])<<32) + (ord(data[7])<<40) + (ord(data[8])<<48) + (ord(data[9])<<56)
        self.routerAddr = (ord(data[12])) + (ord(data[13])<<8) + (ord(data[14])<<16) + (ord(data[15])<<24) +(ord(data[16])<<32) + (ord(data[17])<<40) + (ord(data[18])<<48) + (ord(data[19])<<56)
        # CompositeId is a combination of extAddr and routerAddr
        self.compAddress = (ord(data[2])) + (ord(data[3])<<8) + (ord(data[4])<<16) + (ord(data[5])<<24) + (ord(data[6])<<32) + (ord(data[7])<<40) + (ord(data[8])<<48) + (ord(data[9])<<56) + (ord(data[12])) + (ord(data[13])<<64) + (ord(data[14])<<72) + (ord(data[15])<<80) +(ord(data[16])<<88) + (ord(data[17])<<96) + (ord(data[18])<<104) + (ord(data[19])<<112)
        self.timestamp = datetime.now()
      
        
# TODO: RESEARCH INHERITANCE MODEL
class CpRfMsgExt(CpRfMsg):
    def __init__(self, data):
        CpRfMsg.__init__(self, data)
        self.raw = data
        