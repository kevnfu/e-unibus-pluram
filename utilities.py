import hmac
import os

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

def load_secret(name):
    """read cookie-secret from file"""
    fo = open(os.path.join(os.path.dirname(__file__), 
        'secrets', name))
    secret = fo.readline()
    fo.close()
    return secret
    
COOKIE_SECRET = load_secret('cookie-secret.txt')

# cookie security
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(COOKIE_SECRET, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val