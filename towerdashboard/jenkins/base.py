#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2018-2019 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import flask
import json
import requests

from datetime import datetime
from flask import current_app
from towerdashboard import db
from towerdashboard import github
from towerdashboard.jenkins import jenkins


@jenkins.route('/ansible-versions', strict_slashes=False)
def ansible_versions():
    db_access = db.get_db()

    versions = db_access.execute('SELECT * FROM ansible_versions').fetchall()
    versions = db.format_fetchall(versions)

    return flask.Response(
        json.dumps(versions),
        status=200,
        content_type='application/json'
    )


@jenkins.route('/os-versions', strict_slashes=False)
def os_versions():
    db_access = db.get_db()

    versions = db_access.execute('SELECT * FROM os_versions').fetchall()
    versions = db.format_fetchall(versions)

    return flask.Response(
        json.dumps(versions),
        status=200,
        content_type='application/json'
    )


@jenkins.route('/tower-versions', strict_slashes=False)
def tower_versions():
    db_access = db.get_db()

    versions = db_access.execute('SELECT * FROM tower_versions').fetchall()
    versions = db.format_fetchall(versions)

    return flask.Response(
        json.dumps(versions),
        status=200,
        content_type='application/json'
    )


@jenkins.route('/results', strict_slashes=False, methods=['POST'])
def results():
    payload = flask.request.json

    if 'devel' == payload['tower']:
        tower_query = 'SELECT id FROM tower_versions WHERE code = "devel"'
    else:
        tower_query = 'SELECT id FROM tower_versions WHERE code = "%s"' % payload['tower'][0:3]
    ansible_query = 'SELECT id FROM ansible_versions WHERE version = "%s"' % payload['ansible']
    os_query = 'SELECT id FROM os_versions WHERE version = "%s"' % payload['os']

    db_access = db.get_db()

    db_access.execute(
        'DELETE FROM results WHERE tower_id = (%s) AND ansible_id = (%s) AND os_id = (%s)' % (tower_query, ansible_query, os_query)
    )
    db_access.commit()

    db_access.execute(
        'INSERT INTO results (tower_id, ansible_id, os_id, status, url) VALUES ((%s), (%s), (%s), "%s", "%s")' % (tower_query, ansible_query, os_query, payload['status'], payload['url'])
    )
    db_access.commit()

    return flask.Response(
      json.dumps({'Inserted': 'ok'}),
      status=201,
      content_type='application/json'
    )


def serialize_issue(milestone_number, milestone_name):
    issues = github.get_issues_information(milestone_number)

    needs_test_issues = []
    for issue in issues:
        for label in issue['labels']:
            if label['name'] == 'state:needs_test':
                needs_test_issues.append({
                    'title': issue['title'],
                    'url': issue['html_url'],
                    'updated_at': issue['updated_at'],
                    'assignee': ', '.join([i['login'] for i in issue['assignees']])
                })

    return {
        'count': len(issues),
        'html_url': 'https://github.com/{}/issues?q=is:open+milestone:{}'.format(
            current_app.config.get('TOWERQA_REPO')[:-3], milestone_name
        ),
        'needs_test_count': len(needs_test_issues),
        'needs_test_issues': needs_test_issues,
        'needs_test_html_url': 'https://github.com/{}/issues?q=is:open+milestone:{}+label:state:needs_test'.format(
            current_app.config.get('TOWERQA_REPO')[:-3], milestone_name
        )
    }


@jenkins.route('/releases', strict_slashes=False)
def releases():
    db_access = db.get_db()

    versions_query = 'SELECT * FROM tower_versions'
    versions = db_access.execute(versions_query).fetchall()
    versions = db.format_fetchall(versions)

    results_query = 'SELECT tv.id, tv.version, av.version as "ansible", ov.version as "os", ov.description as "os_description", res.status, res.created_at as "res_created_at", res.url FROM tower_versions tv JOIN tower_os toos ON tv.id = toos.tower_id JOIN os_versions ov on toos.os_id = ov.id JOIN tower_ansible ta ON tv.id = ta.tower_id JOIN ansible_versions av ON av.id = ta.ansible_id LEFT JOIN results res ON (res.tower_id = tv.id AND res.os_id = ov.id AND res.ansible_id = av.id) ORDER BY tv.version, ov.id, av.id'
    results = db_access.execute(results_query).fetchall()
    results = db.format_fetchall(results)

    branches = github.get_branches()
    milestones = github.get_milestones()

    now = datetime.now()
    for result in results:
        if result['res_created_at']:
            delta = now - datetime.strptime(result['res_created_at'], '%Y-%m-%d %H:%M:%S')
            result['freshness'] = delta.days

    for version in versions:
        if 'devel' not in version['version'].lower():
            _version = version['version'].lower().replace(' ', '_')
            _res = [branch for branch in branches if branch.startswith(_version)]
            _res.sort()
            milestone_name = _res[-1]
            version['next_release'] = _res[-1]
            version['next_release'] = version['next_release'].replace('release_', '')
            version['next_release_test_plan'] = github.get_test_plan_url(version['next_release'])
        else:
            version['next_release'] = current_app.config.get('DEVEL_VERSION_NAME', 'undef')
            milestone_name = 'release_{}'.format(version['next_release'])

        milestone_number = milestones.get(milestone_name)
        version['issues'] = serialize_issue(milestone_number, milestone_name) if milestone_number else None

    return flask.render_template('jenkins/releases.html', versions=versions, results=results)
