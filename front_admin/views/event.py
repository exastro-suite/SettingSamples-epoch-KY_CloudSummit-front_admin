#   Copyright 2022 NEC Corporation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import json

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from logging import getLogger

from ..models import event
from ..models import speaker

event_app = Blueprint("event", __name__, template_folder="templates")
logger = getLogger(__name__)

@event_app.route("/", methods=["GET"])
@login_required
def event_list():
    logger.info("call: event_list")

    events = event.get_events()

    upcomings = [x for x in events if server_str_to_datetime(x['event_date']) > datetime.now()]
    upcomings = sorted(upcomings, key=lambda x:x['event_date'], reverse=True)
    upcomings = [
        {
            'event_path': x['event_id'],
            'event_name': x['event_name']
        } for x in upcomings
    ]

    archives = [x for x in events if server_str_to_datetime(x['event_date']) <= datetime.now()]
    archives = sorted(archives, key=lambda x:x['event_date'], reverse=True)
    archives = [
        {
            'event_path': x['event_id'],
            'event_name': x['event_name']
        } for x in archives
    ]

    return render_template(
        "event/event.html", upcomings=upcomings, archives=archives
    )

@event_app.route("/<int:event_id>", methods=["GET"])
@login_required
def event_detail(event_id):
    logger.info("call: event_detail [event_id={}]".format(event_id))

    event_detail = event.get_event_detail(event_id)
    event_detail['event_date'] = exchange_date_to_client(event_detail['event_date'])

    return event_detail

@event_app.route("/", methods=["POST"])
@login_required
def create_event():
    logger.info("call: create_event")

    param = request.json
    param['event_date'] = exchange_date_to_server(param['event_date'])
    event.create_event(param)

    return '', 201

@event_app.route("/<int:event_id>", methods=["PUT"])
@login_required
def update_event(event_id):
    logger.info("call: update_event [event_id={}]".format(event_id))

    param = request.json

    path_event_id = event_id
    param_event_id = param.get('event_id', None)
    if is_int(param_event_id) and path_event_id != int(param_event_id):
        logger.info("Invalid request data: path_event_id={}, param_event_id={}".format(path_event_id, param_event_id))
        return 'invalid data.', 400

    param['event_date'] = exchange_date_to_server(param['event_date'])
    event.update_event(param)

    return '', 204

@event_app.route("/<int:event_id>", methods=["DELETE"])
@login_required
def delete_event(event_id):
    logger.info("call: delete_event [event_id={}]".format(event_id))

    event.delete_event(event_id)

    return '', 204

@event_app.route("/<int:event_id>/timetable", methods=["GET"])
@login_required
def timetable(event_id):
    logger.info("call: timetable")

    # header準備
    event_detail = event.get_event_detail(event_id)

    header_data = {
        "event_name": event_detail['event_name'],
        "menu_item_list": [
            {
                "name": "event list",
                "url_path": "/",
            },
            {
                "name": "event detail",
                "url_path": "/{}".format(event_id),
            }
        ],
    }

    # body準備
    tmp_seminars = event.get_timetable(event_id)
    #speaker_id_list = [x['speaker_id'] for x in tmp_seminars]
    #speakers = speaker.get_speaker(speaker_id_list)
    speakers_dict = {}
    #speakers_dict = { x['speaker_id']: {
    #                    'speaker_name': x['speaker_name'],
    #                    'speaker_profile': x['speaker_profile']
    #                    } for x in speakers}
    master = event.get_master()

    seminars = construct_seminar_data(tmp_seminars, speakers_dict)
    timetable = {
        "seminars": seminars,
        "mst_block": master['block'],
        "mst_classes": master['class'],
    }

    return render_template(
        "event/timetable.html", header_data=header_data, timetable=timetable
    )

def client_str_to_datetime(datetime_str):

    return datetime.strptime(datetime_str, '%Y/%m/%d %H:%M')

def server_str_to_datetime(datetime_str):

    # return datetime.fromisoformat(datetime_str.replace('Z', '+00:00')) # python3.7~
    return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ') # not %z, because https://bugs.python.org/issue15873

def exchange_date_to_client(datetime_str):

    date_obj = server_str_to_datetime(datetime_str)

    return date_obj.strftime('%Y/%m/%d %H:%M')

def exchange_date_to_server(datetime_str):

    date_obj = client_str_to_datetime(datetime_str)

    return date_obj.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')

def construct_seminar_data(tmp_seminars, speakers_dict):

    seminar = {}
    for item in tmp_seminars:

        # debug
        logger.debug(json.dumps(item))

        block_name = item['block_name']
        class_str = str(server_str_to_datetime(item['start_datetime']).hour)
        seminar_title = item['seminar_name']
        seminar_author = ''
        #seminar_author = speakers_dict[item['speaker_id']]['speaker_name']
        if item['participated'] == "true":
            seminar_status = 1
        elif item['capacity_over'] == "true":
            seminar_status = 2
        else:
            seminar_status = 0
        seminar_id = item['seminar_id']

        # block要素が無ければ作成
        if block_name not in seminar:
            seminar[block_name] = {}

        seminar[block_name][class_str] = [seminar_title, seminar_author, seminar_status, seminar_id]

    return seminar

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
