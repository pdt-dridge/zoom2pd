import time
import calendar
import jwt
import requests
import re
import os

from flask import Flask, request, Response
import json
from dotmap import DotMap

import pd

import pprint
pp = pprint.PrettyPrinter(indent=4)

pd_key = os.environ.get('PD_KEY') or "Set your PD_KEY environment variable to a PD API token"
from_email = os.environ.get('FROM_EMAIL') or "Set your FROM_EMAIL environment variable to the login email of a PD user"
zoom_key = os.environ.get('ZOOM_KEY') or "Set your ZOOM_KEY environment variable to a Zoom REST API access key"
zoom_secret = os.environ.get('ZOOM_SECRET') or "Set your ZOOM_SECRET environment variable to your Zoom REST API client secret"

app = Flask(__name__)

def zoom_token():
		zoom_jwt_payload = { 'iss': zoom_key, 'exp': calendar.timegm(time.gmtime()) + 36000 }
		zoom_token = jwt.encode(zoom_jwt_payload, zoom_secret)
		return zoom_token.decode("utf-8")

@app.route("/", methods=['POST'])
def index():
	req = DotMap(request.json)
	if req.event == 'participant_joined' or req.event == 'participant_left':

		meeting_id = req.payload.meeting.id
		meeting_topic = req.payload.meeting.topic
		action = req.event.split('_')[1]
		user_name = req.payload.meeting.participant.user_name
		user_id = req.payload.meeting.participant.user_id

		zoom_req = requests.Request(method="get", 
			url=f"https://api.zoom.us/v2/users/{user_id}", 
			headers={"Authorization": f"Bearer {zoom_token()}"})
		prepped = zoom_req.prepare()
		response = requests.Session().send(prepped)

		user_email = response.json().get("email");
		note = f'{user_name} ({user_email}) {action} Zoom meeting {meeting_id} ({meeting_topic})'
		print(note)
		incidents = pd.fetch(api_key=pd_key, endpoint="incidents", params={"statuses[]": ["triggered", "acknowledged"], "include[]": ["metadata"]})
		conf_bridges = [{"id": incident.get("id"), "metadata": incident.get("metadata")} for incident in incidents if incident.get("metadata")]

		for bridge in conf_bridges:
			if bridge["metadata"].get("conference_number"):
				conf = int(re.findall("[\d]+", bridge["metadata"]["conference_number"].replace('-', ''))[-1])
				if (meeting_id == conf):
					print(f'I should put this note on incident {bridge["id"]} because conference number is {bridge["metadata"]["conference_number"]}')
					r = pd.add_note(api_key=pd_key, incident_id=bridge["id"], from_email=from_email, note=note)
			elif bridge["metadata"].get("conference_url"):
				conf = int(re.findall("[\d]+", bridge["metadata"]["conference_url"].replace('-', ''))[-1])
				if (meeting_id == conf):
					print(f'I should put this note on incident {bridge["id"]} because conference url is {bridge["metadata"]["conference_url"]}')
					r = pd.add_note(api_key=pd_key, incident_id=bridge["id"], from_email=from_email, note=note)

	return "", 200

@app.route("/start", methods=['POST'])
def start_zoom():
	req = DotMap(request.json)
	incident_id = req.messages[0].incident.id
	print(f'incident id is {incident_id}')

	return "", 200