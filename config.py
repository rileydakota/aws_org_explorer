from os import environ

neo4j_config = {
    'host': '127.0.0.1',
    'user': 'neo4j',
    'pass': environ['NEO4JPASS']
}

sts_config = {
    'role_name': 'OrganizationAccountAccessRole'
}

sso_config = {}