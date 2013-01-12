from botoweb.appserver.handlers import RequestHandler
from botoweb.exceptions import BadRequest
from textyserver.resources.user import TextyUser

class UserHandler(RequestHandler):
	
	def __init__(self, env, config):
		pass

	def _post(self, request, response, id=None):
		response.content_type = "application/json"

		user = createUser(request.params)
		try:
			challenge = getChallengeCode()
		except e:
			# retry 
			raise e

		try:
			user.sms(challenge)
		except e:
			# deal with twilio errors
			raise e

		return response

def createUser(params):
	required_params = ["email", "token", "number"]

	missing_fields = []
	for param in required_params:
		if param not in params:
			missing_fields.append(param)
		if missing_fields:
			raise BadRequest("Missing required field(s): %s" % " ".join(missing_fields))

	user = TextyUser()
	user.email = params["email"]
	user.auth_token = params["token"] 
	user.number = params["number"]
	user.status = 

	return user.put()

def getChallengeCode():
	import urllib2
	url = "https://www.random.org/cgi-bin/randstring?num=1&len=%s&digits=%s&upperalpha=%s&loweralpha=%s&unique=on&format=text&rnd=new" % (length, digits, upperalpha, loweralpha)
	headers = {"User-Agent": "%s %s (%s)" % (boto.config.get("app", "name", "skydrive_texty"), boto.config.get("app", "version", "0.1"), boto.config.get("app", "admin_email", ""))}
	req = urllib2.Request(url, None, headers)
	challenge = urllib2.urlopen(req).read().strip()
	return challenge
