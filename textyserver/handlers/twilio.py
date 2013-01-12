from botoweb.appserver.handlers import RequestHandler
import logging
import boto
log = logging.getLogger('texty.twilioHandler')

class TwilioHandler(RequestHandler):


	sqs = boto.connect_sqs()
	text_queue = sqs.lookup("texts")

	def _post(self, request, response, id=None):
		response.content_type = "text/plain"
		log.info(request.params["From"])
		response.body = "Message received."
		return response

