import boto3
from httplib2 import Http
import json
import time


class Workspaces:
    # ====================== Role based connection to AWS resource ===============================
    def __init__(self):
        sts_client = boto3.client('sts')
        assumed_role_object = sts_client.assume_role(
            RoleArn="<ROLE_ARN>",
            RoleSessionName="AssumeRoleSession1"
        )

        credentials = assumed_role_object['Credentials']
        self.connect = boto3.client(
            'workspaces',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        self.paginator = self.connect.get_paginator('describe_workspaces')

    # ====================== Fetches list of Workspace ID's whose status is set to UNHEALTHY =========
    def get_workspace(self, directory_id):
        workspace_id = []
        status = []

        page_response = self.paginator.paginate(
            DirectoryId=directory_id,
            PaginationConfig={
                'MaxItems': 300,
                'PageSize': 25
            }
        )

        for response in page_response:
            for work_id in response["Workspaces"]:
                for key, value in work_id.items():
                    if key == "WorkspaceId":
                        workspace_id.append(value)
                    if key == "State":
                        status.append(value)

        unhealthy_workspaces = []
        if len(workspace_id) == len(status):
            for tups in zip(workspace_id, status):
                for id in tups:
                    if id.__contains__("UNHEALTHY"):
                        unhealthy_workspaces.append(tups[0])

        return unhealthy_workspaces

    # ====================== Reboots UNHEALTHY workspaces returned from get_workspace()================
    def reboot_workspace(self, unhealthy_workspaces):
        for id in unhealthy_workspaces:
            self.connect.reboot_workspaces(RebootWorkspaceRequests=[
                {
                    'WorkspaceId': id
                },
            ]
            )

        time.sleep(30)

        status = []
        i = 1
        while i in range(0,5):
            page_response = self.paginator.paginate(
                WorkspaceIds=unhealthy_workspaces
            )

            for response in page_response:
                for work_id in response["Workspaces"]:
                    for key, value in work_id.items():
                        if key == "State":
                            print("status", value)
                            status.append(value)

            if len(unhealthy_workspaces) == status.count("AVAILABLE"):
                return True
            else:
                status = []
                i = i + 1
                time.sleep(30)

        return False

    # ====================== Sends a Status message to Hangout Chat Room ==============================
    def athens_bot(self, message, url):
        bot_message = {
            "text": message
        }

        message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

        http_obj = Http()

        response = http_obj.request(
            uri=url,
            method='POST',
            headers=message_headers,
            body=json.dumps(bot_message),
        )

        return response


def main():
    obj = Workspaces()
    directory_id = "<DIRECTORY-ID>"

    unhealthy_workspaces = obj.get_workspace(directory_id)

    if unhealthy_workspaces:
        message = "*Athens Workspace Notification:*\n\n" \
                  "```Status      : UNHEALTHY\n" \
                  "WorkspaceIDs : " + str(unhealthy_workspaces) + "```\n" \
                                                                 "*_Rebooting Workspaces..._*\n"

        sucess_mes = "*Athens Workspace Notification:*\n\n" \
                     "*_UNHEALTHY Workspaces are Successfully Rebooted!_*" \
                     "```Status      : AVAILABLE\n" \
                     "WorkspaceIDs : " + str(unhealthy_workspaces) + "```\n"

        fail_mes = "*Athens Workspace Notification:*\n\n" \
                   "*_Some of UNHEALTHY workspaces are not coming to AVAILABLE state. Please check!_*" \
                   "```WorkspaceIDs : " + str(unhealthy_workspaces) + "```\n"

        url = "<HANGOUT_WEBHOOK_URL>"
        
        obj.athens_bot(message, url)

        if obj.reboot_workspace(unhealthy_workspaces) is True:
            obj.athens_bot(sucess_mes, url)
        else:
            obj.athens_bot(fail_mes, url)
    else:
        print("No UNHEALTHY Workspaces found!")


if __name__ == "__main__":
    main()


