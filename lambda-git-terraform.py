#---------------------------------------------------#
# Function designed to parse incoming git messages
# and auto tag our commits to master based on what's
# in the aws-blueprints/version.txt files
#---------------------------------------------------#  

import json
import re
import sys
import base64
import os
from botocore.vendored import requests
from urllib2 import Request, urlopen, URLError, HTTPError

def post_to_slack(name, new_ver):
    slack_hook_url = os.environ.get('slack_hook_url')
    slack_message = {
        'channel': 'terraform-versions',
        'username': "TerraGit",
        'icon_emoji': ':github:',
        'attachments': [
            {
                "fallback": "%s-%s",
                "color": "#36a64f",
                "title": "Terraform Git Tagger",
                "fields": [
                    {
                        "title": name,
                        "value": new_ver,
                        "short": "false"
                    }
                ]
            }
        ]
    }
    print(slack_message)

    req = Request(slack_hook_url, json.dumps(slack_message))

    try:
        response = urlopen(req)
        response.read()
        print("Message posted to %s", slack_message)
    except HTTPError as e:
        print("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        print("Server connection failed: %s", e.reason)
    
def parse_git_sns(data):
    git_token = os.environ.get('git_token')
    git_api_url = os.environ.get('git_api_url')
    headers = {'Authorization': 'token %s' % git_token}

    changed_files = []
    tag_list = []
    modules = {}

    if data["ref"] != "refs/heads/master":
        print("ref not master")
        sys.exit(0)

    for key in data["commits"]:
        if key["distinct"] == True:
            commit_hash = key["id"]

            for obj in key["modified"]:
                changed_files.append(obj)
            for obj in key["added"]:
                changed_files.append(obj)

    for git_file in changed_files:
        if "version.txt" in git_file:
            url = "%s/contents/%s" % (git_api_url, git_file)
            file_r = requests.get(url, headers=headers)
            contents = file_r.json()["content"]
            new_version = base64.b64decode(contents).split('\n', 1)[0].split(":")[1].lstrip()
            module_name = git_file.split("/")[1]
            modules[module_name] = new_version

    for name, ver in modules.iteritems():
        new_ver = name + "-" +  ver
        tag_json = {
            "ref": "refs/tags/%s" % new_ver,
            "sha": commit_hash
        }
        print("New tag: %s" % tag_json)
        tag_headers = {'Authorization': 'token %s' % git_token, 'Content-Type': 'application/json'}
        tag_url = "%s/git/refs" % git_api_url
        tag_r = requests.post(tag_url, headers=tag_headers, json=tag_json)
        print("Tag Response: %s" % tag_r.text)

        if "sha" not in tag_r.text:
            print("No sha found in tag response")
            sys.exit(0)
        else:
            post_to_slack(name, new_ver)

def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']
    print("From SNS: " + message)
    parse_git_sns(json.loads(message))



