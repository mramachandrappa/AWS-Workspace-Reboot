import boto3
from httplib2 import Http
import json
import time


class Workspaces:
#====================== Role based connection to AWS resource ===============================
    def __init__(self):
        sts_client = boto3.client('sts')
        assumed_role_object = sts_client.assume_role(
            RoleArn="<ROLE-ARN>",                       #AWS role arn
            RoleSessionName="AssumeRoleSession1"
        )

        credentials = assumed_role_object['Credentials']
        self.connect = boto3.client(
            'workspaces',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

#====================== Fetches list of Workspace ID's whose status is set to UNHEALTHY =========
    def get_workspace(self, directory_id):
        workspace_id = []
        status = []
        response = None
        token = None
        while True:
            try:
                if token is None:
                    response = self.connect.describe_workspaces(
                        DirectoryId=directory_id
                    )
                elif token is not None:
                    response = self.connect.describe_workspaces(
                        DirectoryId=directory_id,
                        NextToken=token
                    )

                token = response["NextToken"]

                for work_id in response["Workspaces"]:
                    for key, value in work_id.items():
                        if key == "WorkspaceId":
                            workspace_id.append(value)
                        if key == "State":
                            status.append(value)
            except KeyError:
                print("Loop is completed")
                break
            except Exception as e:
                return e

        unhealthy_workspaces = []
        if len(workspace_id) == len(status):
           for tups in zip(workspace_id, status):
                for id in tups:
                    if id.__contains__("UNHEALTHY"):
                        unhealthy_workspaces.append(tups[0])

        return unhealthy_workspaces

#====================== Reboots UNHEALTHY workspaces returned from get_workspace()================
    def reboot_workspace(self, workspaces):
        if workspaces:
            for id in workspaces:
                self.connect.reboot_workspaces(RebootWorkspaceRequests=[
                    {
                    'WorkspaceId': id
                            },
                        ]
                    )

            time.sleep(30)

            status=[]
            i = 0
            while True:
                response = self.connect.describe_workspaces(
                    WorkspaceIds=workspaces
                )

                if i > 8:
                    return False
                else:
                    if len(workspaces) != len(status):
                        for work_id in response["Workspaces"]:
                            for key, value in work_id.items():
                                if key == "State":
                                    print("Current Status {}".format(str(value)))
                                    if value == "AVAILABLE":
                                        status.append(value)
                                    else:
                                        time.sleep(30)
                                        i = i + 1
                    elif len(workspaces) == len(status):
                        break
            return True
        else:
            return False

#====================== Sends a Status message to Hangout Chat Room ==============================
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
    directory_id = "<DIRECTORY_id>" #Workspaces DirectoryID

    workspaces = obj.get_workspace(directory_id)

    if workspaces:
        message = "*Athens Workspace Notification:*\n\n" \
                  "```Status      : UNHEALTHY\n" \
                  "WorkspaceID : " + str(workspaces) + "```\n" \
                  "*_Rebooting Workspaces..._*\n"

        sucess_mes = "*Athens Workspace Notification:*\n\n" \
                     "*_ Unhealthy Workspaces are Successfully Rebooted!_*" \
                     "```Status      : AVAILABLE\n" \
                     "WorkspaceID : " + str(workspaces) + "```\n"

        url = "<Webhook URL>"           # Hangout's Chat room webhook URL
        obj.athens_bot(message, url)

        if obj.reboot_workspace(workspaces) is True:
            obj.athens_bot(sucess_mes, url)
    else:
        print("No UNHEALTHY Workspaces found!")

if __name__ == "__main__":
    main()


