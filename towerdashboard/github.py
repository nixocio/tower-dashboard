#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2019 Red Hat, Inc.
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


import requests

from flask import current_app

API_GITHUB = 'https://api.github.com'


def github_request(url):
    res = requests.get(
        url,
        headers={
            'Authorization': 'token %s' % current_app.config.get('GITHUB_TOKEN'),
            'Accept': 'application/vnd.github.inertia-preview+json'
        }
    )

    return res


def get_project_by_name(name):
    url = '{}/orgs/ansible/projects'.format(API_GITHUB)
    projects = github_request(url).json()

    return [proj for proj in projects if proj['name'] == name][0]


def get_branches():
    url = '{}/repos/{}/branches?per_page=100'.format(
        API_GITHUB, current_app.config.get('TOWERQA_REPO')
    )
    branches = github_request(url).json()
    return [branch['name'] for branch in branches]


def get_test_plan_url(version):
    url = '{}/repos/{}/contents/docs/test_plans/release_validation/testplan-{}.md'.format(
        API_GITHUB, current_app.config.get('TOWERQA_REPO'), version
    )
    res = github_request(url)

    if res.status_code == 200:
        return 'https://github.com/%s/blob/devel/docs/test_plans/release_validation/testplan-%s.md' % (current_app.config.get('TOWERQA_REPO'), version)

    return None


def get_issues_information(project, custom_query=None):
    url = '{}/search/issues?q=is:open+is:issue+project:{}'.format(
        API_GITHUB, project
    )
    if custom_query:
        url += '+{}'.format(custom_query)
    return github_request(url).json()
