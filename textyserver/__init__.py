import boto
import logging
from pyshorturl import Bitly, BitlyError

__version__ = "0.2.0"

CLIENT_ID = boto.config.get("Skydrive", "client_id")
CLIENT_SECRET = boto.config.get("Skydrive", "client_secret")
BITLY_UID = boto.config.get("bitly", "username")
BITLY_API_KEY = boto.config.get("bitly", "api_key")

AUTHCODE_URI = boto.config.get('Texty', 'authcode_uri')
REDIRECT_URI = boto.config.get('Texty', 'redirect_uri')

log = logging.getLogger('texty')
bitly = Bitly(BITLY_UID, BITLY_API_KEY)

def shorten_link(link):
	short_link = link
	try:	
		short_link = bitly.shorten_url(link)
	except BitlyError:
		log.exception("Failed to minify %s with Bitly." % short_link)
	return short_link