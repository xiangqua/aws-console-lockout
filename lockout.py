import json
import boto3
import time

region = 'us-east-1'
queue_url='https://sqs.us-east-1.amazonaws.com/107400677947/login'

#从SQS获取控制台登录消息
def get_messages_from_queue(queue_url):
    """Generates messages from an SQS queue.

    Note: this continues to generate messages until the queue is empty.
    Every message on the queue will be deleted.

    :param queue_url: URL of the SQS queue to drain.

    """
    sqs_client = boto3.client('sqs')

    while True:
        resp = sqs_client.receive_message(
            QueueUrl=queue_url,
            AttributeNames=['All'],
            MaxNumberOfMessages=10
        )

        try:
            yield from resp['Messages']
        except KeyError:
            return

        entries = [
            {'Id': msg['MessageId'], 'ReceiptHandle': msg['ReceiptHandle']}
            for msg in resp['Messages']
        ]
        #
        #消息不主动删除，由SQS根据时间自动删除，具体保留时间在SQS的控制台设置
        #保留时间决定统计周期
        #
        #resp = sqs_client.delete_message_batch(
        #    QueueUrl=queue_url, Entries=entries
        #)

        #if len(resp['Successful']) != len(entries):
        #    raise RuntimeError(
        #        f"Failed to delete messages: entries={entries!r} resp={resp!r}"
        #    )

#统计用户登录失败的次数，返回大于N次失败的用户
def count_login_failure_times(failure_times):
    userlist=[]
    lockuser=[]
    for message in get_messages_from_queue(queue_url):
        body = message['Body']
        message_json = json.loads(body)
        errinfo = message_json['detail']['responseElements']['ConsoleLogin']
        #print(errinfo)
        #如果ConsoleLogin提示的信息为Failure，则放到userlist列表中
        if errinfo =='Failure':
            username=message_json['detail']['userIdentity']['userName']
            userlist.append(username)
        
    #print(userlist)
    from collections import Counter
    #使用counter统计在userlist中的用户出现的次数
    result = Counter(userlist)
    #print(result)
    for i in result:
        print("IAM user " + i + " login failure times: " + str(result[i]))
        #返回失败次数超过默认5次的用户
        if result[i] >= failure_times: 
            lockuser.append(i)
    #print(lockuser)
    return lockuser

def send_mail():
    print("Send mail to notify admin")

def lambda_handler(event, context):
    import boto3
    client = boto3.client('iam')
    #定义具体超过多少次失败锁定用户，默认times=5
    times=5
    #调用函数获取超过次数的用户
    lock_user_list = count_login_failure_times(times)
    if lock_user_list != []:
        #print(lock_user_list)
        for user in lock_user_list:
            #print(user)
            try:
                response = client.delete_login_profile(UserName=user)
                print("Success delete user console access profile: IAM username " + user)
                #发送邮件给相关管理人员提醒
                send_mail()
                print("Success send mail")

            except Exception as e:
                print(e)
    else:
        print("None user need to delete console access " + str(lock_user_list))
