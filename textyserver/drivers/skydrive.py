class SkydriveAccount(object):
	
	def __init__(self, token=None, refresh_token=None):
		self.token = token
		self.refresh_token = refresh_token

	def refresh_authorization(self):
		pass

	def make_request(self):
		pass

