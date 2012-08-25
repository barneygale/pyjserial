all = ['HashMap']

import HashMap
import Default

types = {
    'java.util.HashMap': HashMap
}

def get(t):
    return types.get(t, Default)
