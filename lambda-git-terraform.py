#---------------------------------------------------#  
#     <Christopher Stobie> cstobie@veritone.com     #
#---------------------------------------------------#
# Function designed to parse incoming git messages
# and auto tag our commits to master based on what's
# in the aws-blueprints/version.txt files
#---------------------------------------------------#  

import json
import re
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

def get_secret(secret_name, region_name):
    endpoint_url = "https://secretsmanager.us-east-1.amazonaws.com"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name,
        endpoint_url=endpoint_url
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
    else:
        if 'SecretString' in get_secret_value_response:
            v = json.loads(get_secret_value_response['SecretString'])
            #---------------------------------------------------#  
            # This expects the name of the saved secret to be
            # git_token
            #---------------------------------------------------#  
            secret = v['git_token']
            return(secret)
        else:
            print("Invalid response, missing SecretString")
            sys.exit(1)
    
def parse_git_sns(data):
    repo_name = os.environ.get('repo_name')
    git_token = get_secret('git_token', 'us-east-1')
    headers = {'Authorization': 'token %s' % git_token}

    changed_files = []
    tag_list = []
    modules = {}

    if data["ref"] == "refs/heads/master" or data["ref"] == "refs/heads/govcloud-master":
        for key in data["commits"]:
            if key["distinct"] == True:
                commit_hash = key["id"]

                for obj in key["modified"]:
                    changed_files.append(obj)
                for obj in key["added"]:
                    changed_files.append(obj)

        for git_file in changed_files:
            if "version.txt" in git_file:
                if data["ref"] == "refs/heads/master": 
                    url = "https://api.github.com/repos/%s/contents/%s" % (repo_name, git_file)

                file_r = requests.get(url, headers=headers)
                contents = file_r.json()["content"]
                new_version = base64.b64decode(contents).split('\n', 1)[0].split(":")[1].lstrip().strip()
                module_name = base64.b64decode(contents).split('\n', 1)[0].split(":")[0]
                modules[module_name] = new_version

        for name, ver in modules.iteritems():
            new_ver = name + "-" +  ver
            tag_json = {
                "ref": "refs/tags/%s" % new_ver,
                "sha": commit_hash
            }
            print("New tag: %s" % tag_json)
            tag_headers = {'Authorization': 'token %s' % git_token, 'Content-Type': 'application/json'}
            tag_url = "https://api.github.com/repos/veritone/terraform-modules/git/refs"
            tag_r = requests.post(tag_url, headers=tag_headers, json=tag_json)
            print("Tag Response: %s" % tag_r.text)

            if "sha" not in tag_r.text:
                print("No sha found in tag response")
            else:
                post_to_slack(name, new_ver)

def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']
    print("From SNS: " + message)
    parse_git_sns(json.loads(message))




