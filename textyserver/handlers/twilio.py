from botoweb.appserver.handlers import RequestHandler
import logging
import boto
import json
log = logging.getLogger('texty.twilioHandler')

class TwilioHandler(RequestHandler):


	sqs = boto.connect_sqs()
	text_queue = sqs.lookup("texts")

	def _post(self, request, response, id=None):
		response.content_type = "text/plain"
		payload = json.dumps((request.params["From"], request.params["Body"]))
		msg = self.sqs.new_message(payload)
		self.text_queue.write(msg)
		log.info(request.params["From"])

		return response

