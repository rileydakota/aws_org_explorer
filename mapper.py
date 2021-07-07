import boto3
import botocore

from core.sso import retrieve_aws_sso_token, retrieve_aws_accounts, retrieve_credentials, retrieve_roles_in_account
from core.iamEnum import retreive_roles, retreive_users
from core.db import Db
from core.orgs import get_aws_accounts
from core.sts import assume_role

import concurrent.futures

from config import neo4j_config, sts_config


def get_token_from_cache():
    try:
        with open("token", 'r') as f:
            return f.readline()
    except FileNotFoundError:
        return None


def save_token_to_cache(token):
    with open("token", 'w') as f:
        f.write(token)


def process_account(sso, aws_sso_token, account, db):

    sso_roles = retrieve_roles_in_account(sso, aws_sso_token, account)

    # Loop through roles. If role get permission error on list, try next.
    for access_role in sso_roles:

        print(f"\tListing {account['accountId']} using role, {access_role}")

        aws_access_key_id, aws_secret_access_key, aws_session_token = retrieve_credentials(
            sso, aws_sso_token, account['accountId'], access_role)

        iamClient = boto3.client('iam', aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 aws_session_token=aws_session_token)
        try:
            roles = retreive_roles(iamClient)
            users = retreive_users(iamClient)
            
            for role in roles:
                db.add_aws_role(role)
            for user in users:
                db.add_aws_user(user)

            # If no exceptions were had break this loop and start next account
            break

        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'AccessDenied':
                print(
                    f"\tRole {access_role} does not have permissions to list users/roles...trying next role")
                continue

def process_account_sts(sts, account, db):

    print(f"\tListing {account['Id']} using role, {sts_config['role_name']}")

    aws_access_key_id, aws_secret_access_key, aws_session_token = assume_role(sts, sts_config['role_name'], account['Id'])

    iamClient = boto3.client('iam', aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 aws_session_token=aws_session_token)

    try:
        roles = retreive_roles(iamClient)
        print(roles)
        users = retreive_users(iamClient)
        print(users)
        for role in roles:
            db.add_aws_role(role)
        for user in users:
            db.add_aws_user(user)
            # If no exceptions were had break this loop and start next account
    except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'AccessDenied':
                print(f"\tRole {sts_config['role_name']} does not have permissions to list users/roles...trying next role")

if __name__ == "__main__":
    #aws_sso_token = get_token_from_cache()
    db = Db(neo4j_config['host'], neo4j_config['user'], neo4j_config['pass'])
    #sso = boto3.client('sso', region_name=sso_config['region'])
    orgs = boto3.client('organizations')
    # try:
    #     aws_accounts_list = retrieve_aws_accounts(sso, aws_sso_token)
    # except Exception as error:
    #     aws_sso_token = retrieve_aws_sso_token(None)
    #     save_token_to_cache(aws_sso_token)
    #     aws_accounts_list = retrieve_aws_accounts(sso, aws_sso_token)
    sts = boto3.client('sts')
    iam = boto3.client('iam')
    master_account = sts.get_caller_identity()['Account']
    aws_accounts_list = get_aws_accounts(orgs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        count = 0
        for account in aws_accounts_list:
            db.add_aws_account(account)
            if account['Id'] == master_account:
                print('\tlisting master account {} using current access'.format(master_account))
                roles = retreive_roles(iam)
                users = retreive_users(iam)
                for role in roles:
                    db.add_aws_role(role)
                for user in users:
                    db.add_aws_user(user)
            else:
                futures.append(executor.submit(
                    process_account_sts,sts, account, db))
            

        for future in concurrent.futures.as_completed(futures):
            count += 1
            print(f"Completed ({count}/{len(aws_accounts_list)})")
