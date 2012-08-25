import struct

STREAM_MAGIC      = '\xAC\xED'
STREAM_VERSION    = 5

TC_NULL           = 0x70
TC_REFERENCE      = 0x71
TC_CLASSDESC      = 0x72
TC_OBJECT         = 0x73
TC_STRING         = 0x74
TC_ARRAY          = 0x75
TC_CLASS          = 0x76
TC_BLOCKDATA      = 0x77
TC_ENDBLOCKDATA   = 0x78
TC_RESET          = 0x79
TC_BLOCKDATALONG  = 0x7A
TC_EXCEPTION      = 0x7B
TC_LONGSTRING     = 0x7C
TC_PROXYCLASSDESC = 0x7D
TC_ENUM           = 0x7E

baseWireHandle = 0x7E0000

SC_WRITE_METHOD   = 0x01 #if SC_SERIALIZABLE
SC_SERIALIZABLE   = 0x02
SC_EXTERNALIZABLE = 0x04
SC_BLOCK_DATA     = 0x08 #if SC_EXTERNALIZABLE
SC_ENUM           = 0x10

class Node:
    def __init__(self, parent):
        #print "Initialising %s" % self.__class__
        self.b = parent.b
        self.parent = parent
        self.decode()
        
    @classmethod
    def get_leaf(self, i):
        return self(i)
    
    def get_root(self):
        return self.parent.get_root()
    
    def assign_handle(self, *args):
        i = args[0] if args else self
        self.get_root().assign_handle(i)
    
    def reset_handles(self):
        self.get_root().reset_handles()
    
    def get_handle(self, i):
        return self.get_root().get_handle(i)
    
    def read_values(self):
        for f in self.fields:
            f.decode()
    
    @classmethod
    def unpack_real_peek(self, buff, dt):
        d = buff.peek(struct.calcsize('>'+dt))
        if d == '': return None
        return struct.unpack('>'+dt, d[0])[0]
    
    def unpack_real(self, buff, dt):
        return struct.unpack('>'+dt, buff.read(struct.calcsize('>'+dt)))[0]
    
    def unpack(self, dt):
        return self.unpack_real(self.b, dt)
    
    def unpack_string(self):
        l = self.unpack('h')
        return self.b.read(l)
    
    def unpack_long_string(self):
        l = self.unpack('q')
        return self.b.read(l)
    
class ProxyNode(Node):
    @classmethod
    def get_leaf(self, i):
        t1 = self.unpack_real_peek(i.b, 'B')
        for t2 in self.types:
            a = t2.get_leaf(i)
            if a != None:
                return a
        
        return None

class TypedNode(Node):
    def __init__(self, parent):
        #print "Initialising %s" % self.__class__
        
        self.b = parent.b
        self.parent = parent
       
        
        ty = self.unpack('B')
        assert ty == self.ty
        
        self.decode()
    
    @classmethod
    def get_leaf(self, i):
        if self.unpack_real_peek(i.b, 'B') == self.ty:
            return self(i)
        else:
            return None
    def decode(self):
        pass
    


###
### TYPED NODES!
###

class JNullReference(TypedNode):
    ty = TC_NULL

class JPrevObject(TypedNode):
    ty = TC_REFERENCE
    def decode(self):
        self.pointer = self.get_handle(self.unpack('i'))

class JNewRegularClassDesc(TypedNode):
    ty = TC_CLASSDESC
    def decode(self):
        self.name = self.unpack_string()
        self.serialVersionUID = self.unpack('Q')
        self.assign_handle()
        self.flags = self.unpack('B')
        self.field_count = self.unpack('h')
        self.fields = []
        for i in range(self.field_count):
            self.fields.append(JFieldDesc.get_leaf(self))
        
        self.annotation = JContents.get_leaf(self)
        self.superClass = JClassDesc.get_leaf(self)

class JNewObject(TypedNode):
    ty = TC_OBJECT
    def decode(self):
        self.classDesc = JClassDesc.get_leaf(self)
        self.assign_handle()
        if SC_SERIALIZABLE & self.classDesc.flags:
            self.read_values()
            if SC_WRITE_METHOD & self.classDesc.flags:
                self.annotation = JContents.get_leaf(self)
        elif SC_EXTERNALIZABLE & self.classDesc.flags:
            if SC_BLOCKDATA & self.classDesc.flags:
                self.annotation = JContents.get_leaf(self)
            else:
                #TODO:
                read_external(self)

    def read_values(self):
        self.values = []
        for f in self.classDesc.fields:
            self.values.append(f.decode2())

class JNewRegularString(TypedNode):
    ty = TC_STRING
    def decode(self):
        self.assign_handle()
        self.data = self.unpack_string()

class JNewArray(TypedNode):
    ty = TC_ARRAY
    def decode(self):
        self.classDesc = JClassDesc.get_leaf(self)
        self.assign_handle()
        self.size = self.unpack('I')
        #TODO
        self.data = self.unpack_array(self.classDesc.something, self.size)

class JNewClass(TypedNode):
    ty = TC_CLASS
    def decode(self):
        self.classDesc = JClassDesc.get_leaf(self)
        self.assign_handle()

class JBlockDataShort(TypedNode):
    ty = TC_BLOCKDATA
    def decode(self):
        self.length = self.unpack('B')
        self.data = self.b.read(self.length)

class JReset(TypedNode):
    ty = TC_RESET
    def decode(self):
        self.reset_handles()


class JBlockDataLong(TypedNode):
    ty = TC_BLOCKDATALONG
    def decode(self):
        self.length = self.unpack('i')
        self.data = self.b.read(self.length)

class JException(TypedNode):
    ty = TC_EXCEPTION
    def decode(self):
        self.reset_handles()
        self.throwable = JObject.get_leaf(self)
        self.reset_handles()


class JNewLongString(TypedNode):
    ty = TC_LONGSTRING
    def decode(self):
        self.assign_handle()
        self.data = self.unpack_long_string()

class JNewProxyClassDesc(TypedNode):
    ty = TC_PROXYCLASSDESC
    def decode(self):
        self.assign_handle()
        self.proxyInterfaceCount = self.unpack('I')
        self.proxyInterfaceNames = []
        for i in range(self.proxyInterfaceCount):
            self.proxyInterfaceNames.append(self.unpack_string())
        
        self.annotation = JContents.get_leaf(self)
        self.superclass = JClassDesc.get_leaf(self)

class JNewEnum(TypedNode):
    ty = TC_ENUM
    def decode(self):
        self.classDesc = JClassDesc.get_leaf(self)
        self.assign_handle()
        self.enumConstantName = self.unpack_string()

###
### Special nodes
###

class JStream(Node):
    handles = []
    def __init__(self, buff):
        self.parent = None
        self.b = buff
        self.decode()
        
    def decode(self):
        self.magic = self.b.read(2)
        assert self.magic == STREAM_MAGIC
        self.version = self.unpack('h')
        assert self.version == STREAM_VERSION
        
        #read contents
        self.data = JContents.get_leaf(self)
    def get_root(self):
        return self
    def assign_handle(self, n):
        self.handles.append(n)
    def reset_handles(self):
        self.handles = []
    def get_handle(self, i):
        return self.handles[i-baseWireHandle]

class JFieldDesc(Node):
    primatives = {
        'C': 'c', #character
        'B': 'b', #byte
        'D': 'd', #double
        'F': 'f', #float
        'I': 'i', #int
        'J': 'q', #long (note: java's long is 8 bytes)
        'S': 'h', #short
    }
    objects = {
        '[': JNewArray,
        'L': JNewObject
    }
    def decode(self):
        self.ty = self.unpack('c')
        assert self.ty in self.primatives.keys() + self.objects.keys()
        self.name = self.unpack_string()
        if self.ty in self.objects:
            self.classname = self.unpack_string()
            self.decode2 = lambda: self.objects[self.ty].get_leaf(self)
        elif self.ty in self.primatives:
            self.decode2 = lambda: self.unpack(self.primatives[self.ty])


class JContents(Node):
    def decode(self):
        self.children = []
        while True:
            t1 = self.unpack_real_peek(self.b, 'B')
            if t1 == None:
                break
            if t1 == TC_ENDBLOCKDATA:
                self.unpack('B')
                break
            
            self.children.append(JContent.get_leaf(self))


###
### Container nodes
###

class JBlockData(ProxyNode):
    types = (JBlockDataShort, JBlockDataLong)

class JNewString(ProxyNode):
    types = (JNewRegularString, JNewLongString)

class JNewClassDesc(ProxyNode):
    types = (JNewRegularClassDesc, JNewProxyClassDesc)    

class JClassDesc(ProxyNode):
    types = (JNewClassDesc, JNullReference, JPrevObject)

class JObject(ProxyNode):
    types = (JNewObject, JNewClass, JNewArray, JNewString, JNewEnum, JNewClassDesc, JPrevObject, JNullReference, JException, JReset)

class JContent(ProxyNode):
    types = (JObject, JBlockData)
