import tree
import jtypes
import re

def fold_properties(o):
    
    return dict(zip([f.name for f in o.classDesc.fields], o.values))

def unserialize(f):
    root = tree.JStream(f)
    out = []
    for c in root.data.children:
        if isinstance(c, tree.JNewObject):
            handler = jtypes.get(c.classDesc.name)
            classname = re.sub('^.*\.', '', c.classDesc.name)
            
            props = {'_java': fold_properties(c)}
            
            print classname, handler.base, props
            o = type(classname, handler.base, props)()
            
            handler.extend(c, o)
            
            out.append(o)
        else:
            raise Exception("Unhandled content type")
    
    return out
