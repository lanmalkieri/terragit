## Terragit
This is a lambda function designed around reading a version.txt file from a terraform repo (or any repo really) and when a commit hits master, tagging that commit with whatever is in version.txt. This was designed for my use for Terraform Modules tagging, but it could really work for whatever.

#### Required Lambda Environment Variables
- git\_api_url: URL to the API for github with your repo's specific information
	- EXAMPLE: `https//api.github.com/repos/dummyorg/terraform-modules`
- slack\_hook_url: URL For Slack Hook
- repo_name: The name of the repo to look for, like lanmalkieri/terraform-modules


#### AWS Secret Manager
- This now supports AWS Secret Manager. https://aws.amazon.com/secrets-manager/
- Create a secret called git_token and ensure your function has access to decrypt the secret 


Follow [these](https://aws.amazon.com/blogs/compute/dynamic-github-actions-with-aws-lambda/) instructions to setup github/aws/sns integrations. 

Create your lambda function using this script.

Magic.


Make sure in your terraform-modules repo you are using version.txt files in each of your modules/blueprints, and that the top line of the file looks like:
`name: 1.0.0`
