import io
import pyjserial

f = io.open('persistance.ser', 'rb')
stuff = pych.fold.unserialize(f)
f.close()

for k, v in stuff[0].iteritems():
    print k, v
#print stuff[0]._java
