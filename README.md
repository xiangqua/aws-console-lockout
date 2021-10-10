
# 利用Serverless架构实现AWS控制台密码锁定策略

## 背景介绍
AWS账户在尝试指定的登录失败次数后，无法创建“锁定策略”来锁定用户。为了增强AWS账户安全性，本文将利用Amazon Lambda和Amazon SQS结合Amazon CloudWatch Event实现自定义密码重试锁定策略以增强AWS IAM用户安全，并满足用户需要PCI-DSS或等保认证的审核条款。

PCI-DSS认证条款对需要具备lockout功能的描述：

| list  | describe  | 
| :------------: |:---------------:| 
| PCI Requirement 8.1.6      | Limit Repeated Access Attempts by Locking Out User ID After No More Than Six Attempts     | 
| PCI Requirement 8.1.7      | Set lockout duration to a minimum of 30 minutes or until an administrator enables the user ID.    |



## 功能简介
整个架构全部由无服务器服务构建，用到了Amazon Lambda、Amazon SQS、Amazon CloudWatch Event、Amazon SNS服务，一经部署不需要用户维护底层架构。


<img src="https://user-images.githubusercontent.com/75667661/136677334-64fc9b0a-c484-45a4-8ea7-b31a783a734c.png" width="970" height="400"/><br/>

实现的功能如下：

 * 默认在60s内对console登陆消息进行统计一次，如果一个用户在1分钟内超过5次的错误登陆，将对该用户进行锁定

 * 直到管理员手工解锁用户，否则该用户将无法继续登陆控制台

 * 在锁定账户的同时，可以触发通知信息，通知管理员对应的锁定信息发生以便进行干预操作或审计操作

 * 所有锁定操作都会记录在lambda的cloudwatch日志中，可以通过日志对关闭操作进行分析

  
## 部署步骤说明
因为AWS海外控制台的默认Amazon CloudWatch Event事件生成在us-east-1，所以所有的服务部署在us-east-1

### 1、	创建Amazon SQS标准队列

1.1	进入到Amazon SQS控制台选择：创建队列

1.2	默认选择队列类型为：标准

1.3	填入队列名称，例如：lockout.sqs

1.4	在配置项中，修改如下两个参数，将可见性超时事件设置为5分钟，将消息保留周期设置为5分钟

1.5	其他选择默认，然后点击：创建队列

### 2、	在Amazon Lambda中部署lockout.py脚本

2.1 在控制台选择创建创建函数

2.2 填入函数名称，例如：lockout

2.3 运行时：选择python3.7

2.4 点击创建函数

2.5 在函数代码区域，将代码库中内容lockout.py替换lambda_function.py的内容（注：替换里面的queue_url为上一步创建的SQS队列的url）

2.6 在基本设置中，根据实际情况编辑内存大小，例如100M，超时时间设为5分钟

2.7 完成lambda函数创建

2.8 创建完lambda后，修改lambda绑定role的权限，需要附加读取Amazon SQS消息和IAM服务DeleteLoginProfile的权限


lockout.py

### 3、	创建Amazon CloudWatch Event规则

3.1 在控制台进入Amazon Cloudwatch event规则菜单

3.2 点击创建规则

3.3 服务名称选择：AWS控制台登录

3.4 添加目标，选择 SQS队列名称，其它选择默认，点击下一步

3.4 填入规则名称，例如：lockoutrule1

3.5 点击创建规则

3.6再创建另外一条规则

3.7 选择类型为“计划”类型

3.8 固定频率选择1分钟

3.9 添加目标，选择lambda函数，选择上面创建的lambda函数lockout

3.10 下一步填入名称：例如:lockoutrule2

3.11 点击创建规则

### 4、	验证部署

选择合适的测试用户，在控制台登录接入连续输入多次错误密码（默认5次失败锁定，可以在lockout.py中修改），然后在IAM控制台查看对应用户是否被取消了控制台登录权限。在CloudWatch logs中可以看到具体Lambda函数判断和锁定用户的详细日志。
