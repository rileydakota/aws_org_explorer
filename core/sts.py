import boto3

def assume_role(client, role_name, account_id):
    resp = client.assume_role(
        RoleArn='arn:aws:iam::{}:role/{}'.format(
            account_id,
            role_name
        ),
        RoleSessionName='AWS_ORG_EXPLORER'
    )
    credentials = resp.get('Credentials')
    return credentials.get('AccessKeyId'), credentials.get('SecretAccessKey'), credentials.get('SessionToken')