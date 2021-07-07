import boto3

def get_aws_accounts(client):
    res = client.list_accounts()
    accounts = res["Accounts"]

    while res.get("NextToken"):
        res = client.list_accounts(NextToken=res.get("NextToken"))
        accounts.extend = res["Accounts"]

    return accounts
