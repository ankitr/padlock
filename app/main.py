#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2013 Ankit Ranjan
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import unicode_literals #Making everything unicode. It helps with the JSON.

#Preparing import of third-party libraries.
import sys
sys.path.insert(0, 'libs')

import cgi
import datetime
import hashlib
import jinja2
import json
import logging
import webapp2
import os

from google.appengine.api import app_identity
from google.appengine.api import capabilities
from google.appengine.api import channel
from google.appengine.api import images
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import search
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import ndb

#Base Variables
__version__ = '0.1.0'

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

#Functions
def return_error(self, error_string, status_code=400):
	"""return_error()

	Returns error JSON in the result of a failed API call.

	Args:
		self: The self object passed to the function.
		error_string (str): A brief explanation of the error.
		status_code (int): The HTTP error code to be displayed to the user. Default 400.

	Returns:
		None
	"""
	self.response.headers['Content-Type'] = b'application/json'
	self.response.set_status(status_code)
	self.response.out.write(json.dumps({'Error':error_string}, default=json_handler))
	return

def entities_to_keys(entities):
	"""Takes a list of NDB entities and retrieves their NDB keys."""
	keys = []
	for entity in entities:
		keys.append(entity.key)
	return keys

def entities_to_ids(entities):
	"""Takes a list of NDB entities and retrieves their NDB IDs."""
	ids = []
	for entity in entities:
		ids.append(entity.key.id())
	return ids

def keys_to_ids(keys):
	"""Takes a list of NDB keys and retrieves their NDB IDs."""
	ids = []
	for key in keys:
		ids.append(key.id())
	return ids

json_handler = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None

#Models
class Example(ndb.Model):
	attribute = ndb.StringProperty()
	another_one = ndb.IntegerProperty()

#Exception Handlers
def handle_404(request, response, exception):
	logging.info(exception)
	template = jinja_environment.get_template('templates/error/404.html')
	response.headers['Content-Type'] = b'text/html'
	response.write(template.render())
	response.set_status(404)

def handle_500(request, response, exception):
	logging.info(exception)
	template = jinja_environment.get_template('templates/error/500.html')
	response.headers['Content-Type'] = b'text/html'
	response.write(template.render())
	response.set_status(500)

#Handlers
class MainHandler(webapp2.RequestHandler):
    def get(self):
    	template = jinja_environment.get_template('templates/index.html')
		self.response.headers['Content-Type'] = b'text/html'
		self.response.out.write(template.render())

class APIHandler(webapp2.RequestHandler):
	def get(self):
		if not ndb.READ_CAPABILITY.is_enabled():
			logging.critical('Datastore is in write-only mode.')
			return_error(self, 'Datastore is in write-only mode.', 503)
			return
		request_type = self.request.get('request_type')
		if not request_type:
			template = jinja_environment.get_template('templates/error/404.html')
			self.response.headers['Content-Type'] = b'text/html'
			self.response.out.write(template.render())
			self.response.set_status(404)
		if request_type == 'example':
			example_id = self.request.get('example_id')
			if not example_id:
				return_error(self, 'Insufficient information provided.', 400)
				return
			example = Example.get_by_id(example_id)
			if not example:
				return_error(self, 'Example can not be found.', 404)
				return
			response = {
			'attribute': example.attribute,
			'another_one' example.another_one
			}
			self.response.headers['Content-Type'] = b'application/json'
			self.response.out.write(json.dumps(response), default=json_handler)
			return
		else:
			self.error(400)
			return
	def post(self):
		if not ndb.WRITE_CAPABILITY.is_enabled(): #Checks if datastore is in read-only mode (more likely than write-only, but still very unlikely).
			logging.critical('Datastore is in read-only mode.')
			return_error(self, 'Datastore is in read-only mode.', 503)
			return
		request_type = self.request.get('request_type')
		if not request_type:
			return_error(self, 'No request_type detected.', 404)
			return
		if request_type == 'example':
			attribute = self.request.get('attribute')
			another_one = self.request.get('another_one')
			if not attribute or not another_one:
				return_error(self, 'Insufficient information provided.', 400)
				return
			example = Example(attribute=attribute,
			                  another_one=another_one)
			example_key = example.put()
			self.response.headers['Content-Type'] = b'application/json'
			self.response.out.write(json.dumps({'Success':'Example created.', 'example_id':example_key.id()}), default=json_handler)
			return
		else:
			self.error(400)
			return

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500

api = webapp2.WSGIApplication([
	('/api', APIHandler)
], debug=True)