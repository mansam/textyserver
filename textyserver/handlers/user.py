from botoweb.appserver.handlers import RequestHandler
from botoweb.exceptions import BadRequest, NotFound
from textyserver.resources.user import TextyUser
import logging
import json
import boto
import urllib
import requests
import textyserver

log = logging.getLogger('texty.userHandler')

class UserHandler(RequestHandler):

	def _get(self, request, response, id=None):
		if id:
			params = id.split('/')
			if params:
				if params[0] == "code":
					log.info(request)
					user_params = {}

					auth_code = request.params["code"]
					log.info(auth_code)
					state = request.params["state"]
					phone, email = state.split(' ')
					user_params["phone"] = phone
					user_params["email"] = email

					resp = getLiveConnectTokens(auth_code)
					log.info(resp)
	
					user_params["auth_token"] = resp["access_token"]
					user_params["refresh_token"] = resp["refresh_token"]
					createUser(user_params)
					try:
						challenge = getChallengeCode()
					except Exception:
						# retry 
						raise
					try:
						user.sms(challenge)
					except Exception:
						# deal with twilio errors
						raise
					response.body = json.dumps(user.to_dict()) 
		return response

	def _post(self, request, response, id=None):
		response.content_type = "application/json"
		if id:
			params = id.split('/')
			if params:
				if params[0] == "token":
					pass
		else:
			pass
		return response

	def _put(self, request, response, id=None):
		required_params = ["email", "refresh"]
		missing_fields = []
		for param in required_params:
			if param not in request.params:
				missing_fields.append(param)
		if missing_fields:
			raise BadRequest("Missing required field(s): %s" % " ".join(missing_fields))

		try:
			user = TextyUser.find(email=request.params.email).next()
		except StopIteration:
			raise NotFound("No such user.")

		user.refresh_token = request.params["refresh"]
		user.put()

		return response

def getLiveConnectTokens(auth_code):
	base_url = "https://login.live.com/oauth20_token.srf"
	params = {
		"grant_type" : "authorization_code",
		"redirect_uri" : "http:/www.buildanavy.com/user/code",
		"client_id": textyserver.CLIENT_ID,
		"client_secret": textyserver.CLIENT_SECRET,
		"code": auth_code
	}
	return requests.post(base_url, data=params, headers={"content-type":"application/x-www-form-urlencoded"}).json()

def createUser(params):
	required_params = ["email", "phone", "auth_token", "refresh_token"]
	log.info(params)
	missing_fields = []
	for param in required_params:
		if param not in params:
			missing_fields.append(param)
	if missing_fields:
		raise BadRequest("Missing required field(s): %s" % " ".join(missing_fields))

	user = TextyUser()
	user.email = params["email"]
	user.phone = params["phone"]
	user.auth_token = params["auth_token"]
	user.refresh_token = params["refresh_token"]

	return user.put()

def getChallengeCode():
	import urllib2
	length = "6"
	digits = "on"
	loweralpha = "on"
	upperalpha = "off"
	url = "https://www.random.org/cgi-bin/randstring?num=1&len=%s&digits=%s&upperalpha=%s&loweralpha=%s&unique=on&format=text&rnd=new" % (length, digits, upperalpha, loweralpha)
	headers = {"User-Agent": "%s %s (%s)" % (boto.config.get("app", "name", "skydrive_texty"), boto.config.get("app", "version", "0.1"), boto.config.get("app", "admin_email", ""))}
	req = urllib2.Request(url, None, headers)
	challenge = urllib2.urlopen(req).read().strip()
	return challenge
