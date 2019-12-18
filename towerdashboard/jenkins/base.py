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
    if 'ansible' in payload:
        ansible_query = 'SELECT id FROM ansible_versions WHERE version = "%s"' % payload['ansible']
    os_query = 'SELECT id FROM os_versions WHERE version = "%s"' % payload['os']

    db_access = db.get_db()

    if 'ansible' in payload:
        _del_query = 'DELETE FROM results WHERE tower_id = (%s) AND ansible_id = (%s) AND os_id = (%s)' % (tower_query, ansible_query, os_query)
        _ins_query = 'INSERT INTO results (tower_id, ansible_id, os_id, status, url) VALUES ((%s), (%s), (%s), "%s", "%s")' % (tower_query, ansible_query, os_query, payload['status'], payload['url'])
    else:
        _del_query = 'DELETE FROM results WHERE tower_id = (%s) AND os_id = (%s)' % (tower_query, os_query)
        _ins_query = 'INSERT INTO results (tower_id, os_id, status, url) VALUES ((%s), (%s), "%s", "%s")' % (tower_query, os_query, payload['status'], payload['url'])

    db_access.execute(_del_query)
    db_access.commit()
    db_access.execute(_ins_query)
    db_access.commit()

    return flask.Response(
      json.dumps({'Inserted': 'ok'}),
      status=201,
      content_type='application/json'
    )


@jenkins.route('/sign_off_jobs', strict_slashes=False, methods=['POST', 'GET'])
def sign_off_jobs():
    def form_tower_query(tower):
        if 'devel' == tower:
            return 'SELECT id FROM tower_versions WHERE code = "devel"'
        else:
            return 'SELECT id FROM tower_versions WHERE code = "%s"' % tower[0:3]

    if flask.request.method == 'GET':
        tower_query = ''
        for arg in flask.request.args:
            if arg == 'tower':
                tower_query = form_tower_query(flask.request.args.get(arg))
            else:
                return flask.Response(
                    json.dumps({'Error': 'only able to filter on tower versions'}),
                    status=400,
                    content_type='application/json'
                )
        if tower_query:
            job_query = 'SELECT * FROM sign_off_jobs WHERE tower_id = (%s)' % (tower_query)
        else:
            job_query = 'SELECT * FROM sign_off_jobs'

        db_access = db.get_db()
        res = db_access.execute(job_query).fetchall()
        sign_off_jobs = db.format_fetchall(res)

        return flask.Response(
            json.dumps(sign_off_jobs),
            status=200,
            content_type='application/json'
        )
    else:
        payload = flask.request.json
        required_keys = ['tower', 'component', 'deploy', 'platform', 'tls', 'fips', 'ansible']
        missing_keys = []
        for key in required_keys:
            if key not in payload:
                missing_keys.append(key)
        if missing_keys:
            return flask.Response(
            json.dumps({'Error': 'Missing required keys/value pairs for {}'.format(missing_keys)}),
            status=400,
            content_type='application/json'
            )
        tower_query = form_tower_query(payload['tower'])
        job_query = 'SELECT id FROM sign_off_jobs WHERE tower_id = (%s) AND component = "%s" AND deploy = "%s" AND platform = "%s" AND tls = "%s" AND fips = "%s" AND ansible = "%s"' % (tower_query, payload['component'], payload['deploy'], payload['platform'], payload['tls'], payload['fips'], payload['ansible'])
        return_info_query = 'SELECT display_name, created_at FROM sign_off_jobs WHERE id = (%s)' % (job_query)

        db_access = db.get_db()

        _update_query = 'UPDATE sign_off_jobs SET status = "%s", url = "%s", created_at = "%s" WHERE id = (%s)' % (payload['status'], payload['url'], datetime.now(), job_query)
        db_access.execute(_update_query)
        res = db_access.execute(return_info_query).fetchall()
        updated_job = db.format_fetchall(res)
        db_access.commit()

        if updated_job:
            return flask.Response(
            json.dumps(updated_job),
            status=200,
            content_type='application/json'
            )
        else:
            return flask.Response(
            json.dumps({'Error': 'No job found to update'}),
            status=400,
            content_type='application/json'
            )


def serialize_issues(project):
    total_count = github.get_issues_information(project)['total_count']
    result = github.get_issues_information(project, 'label:state:needs_test')

    needs_test_issues = []
    for issue in result['items']:
        needs_test_issues.append({
            'title': issue['title'],
            'url': issue['html_url'],
            'updated_at': datetime
                .strptime(issue['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
                .strftime('%b %-d %Y, %X'),
            'assignee': ', '.join([i['login'] for i in issue['assignees']])
        })

    return {
        'count': total_count,
        'html_url': 'https://github.com/issues?q=is:open+is:issue+project:{}'.format(
            project
        ),
        'needs_test_count': len(needs_test_issues),
        'needs_test_issues': needs_test_issues,
        'needs_test_html_url': 'https://github.com/issues?q=is:open+is:issue+project:{}+label:state:needs_test'.format(
            project
        )
    }


@jenkins.route('/releases', strict_slashes=False)
def releases():
    db_access = db.get_db()

    versions_query = 'SELECT * FROM tower_versions'
    versions = db_access.execute(versions_query).fetchall()
    versions = db.format_fetchall(versions)

    results_query = 'SELECT tv.id, tv.version, av.version as "ansible", ov.version as "os", ov.description as "os_description", res.status, res.created_at as "res_created_at", res.url FROM tower_versions tv JOIN tower_os toos ON tv.id = toos.tower_id JOIN os_versions ov on toos.os_id = ov.id AND ov.version != "OpenShift" AND ov.version != "Artifacts" JOIN tower_ansible ta ON tv.id = ta.tower_id JOIN ansible_versions av ON av.id = ta.ansible_id LEFT JOIN results res ON (res.tower_id = tv.id AND res.os_id = ov.id AND res.ansible_id = av.id) ORDER BY tv.version, ov.id, av.id'
    results = db_access.execute(results_query).fetchall()
    results = db.format_fetchall(results)

    misc_query = 'SELECT tv.id, tv.version, ov.version as "os", ov.description as "os_description", res.status, res.created_at as "res_created_at", res.url FROM tower_versions tv JOIN tower_os toos ON tv.id = toos.tower_id JOIN os_versions ov on toos.os_id = ov.id AND (ov.version == "OpenShift" OR ov.version == "Artifacts") LEFT JOIN results res ON (res.tower_id = tv.id AND res.os_id = ov.id) ORDER BY tv.version, ov.id'
    misc_results = db_access.execute(misc_query).fetchall()
    misc_results = db.format_fetchall(misc_results)

    sign_off_jobs_query = 'SELECT * from sign_off_jobs;'
    sign_off_jobs = db_access.execute(sign_off_jobs_query).fetchall()
    sign_off_jobs = db.format_fetchall(sign_off_jobs)

    unstable_jobs_query = 'SELECT * from sign_off_jobs WHERE status = "UNSTABLE";'
    unstable_jobs = db_access.execute(unstable_jobs_query).fetchall()
    unstable_jobs = db.format_fetchall(unstable_jobs)

    failed_jobs_query = 'SELECT * from sign_off_jobs WHERE status = "FAILURE";'
    failed_jobs = db_access.execute(failed_jobs_query).fetchall()
    failed_jobs = db.format_fetchall(failed_jobs)

    branches = github.get_branches()

    def set_freshness(items, key, discard_old=False):
        for item in items:
            if item.get(key):
                delta = datetime.now() - datetime.strptime(
                    item[key], '%Y-%m-%d %H:%M:%S'
                )
                item['freshness'] = delta.days
        if discard_old:
            items = [ x for x in items if x['freshness'] < 2 ]

        return items

    results = set_freshness(results, 'res_created_at')
    sign_off_jobs = set_freshness(sign_off_jobs, 'created_at')
    unstable_jobs = set_freshness(unstable_jobs, 'created_at', discard_old=True)
    failed_jobs = set_freshness(failed_jobs, 'created_at', discard_old=True)
    misc_results = set_freshness(misc_results, 'res_created_at')

    for version in versions:
        if 'devel' not in version['version'].lower():
            _version = version['version'].lower().replace(' ', '_')
            _res = [branch for branch in branches if branch.startswith(_version)]
            _res.sort()
            milestone_name = _res[-1]
            version['next_release'] = _res[-1]
            version['next_release'] = version['next_release'].replace('release_', '')
        else:
            version['next_release'] = current_app.config.get('DEVEL_VERSION_NAME', 'undef')
            milestone_name = 'release_{}'.format(version['next_release'])

        version['next_release_test_plan'] = github.get_test_plan_url(version['next_release'])
        project_number = github.get_project_by_name('Ansible Tower {}'.format(version['next_release']))['number']
        version['project'] = 'https://github.com/orgs/ansible/projects/{}'.format(project_number)
        version['issues'] = serialize_issues('ansible/{}'.format(project_number))

    return flask.render_template(
        'jenkins/releases.html',
        versions=versions,
        results=results,
        misc_results=misc_results,
        sign_off_jobs=sign_off_jobs,
        unstable_jobs=unstable_jobs,
        failed_jobs=failed_jobs
    )
