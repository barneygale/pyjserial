import struct

base = (dict,)

def extend(node, o):
    a = node.annotation.children
    raw = a[0].data
    o._java['capacity'], o._java['size'] = struct.unpack('>II', raw)
    o.update(dict(zip([d.data for d in a[1::2]], [d.data for d in a[2::2]])))
