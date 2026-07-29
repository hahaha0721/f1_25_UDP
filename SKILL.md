1.ssh
ssh是一种远程连接服务器的协议，它允许用户通过网络安全地访问和管理远程计算机。使用ssh，用户可以在本地计算机上执行命令、传输文件以及进行远程管理，而无需物理访问服务器。ssh通常使用公钥加密技术来确保连接的安全性，并且支持多种身份验证方法，如密码认证和基于密钥的认证。
ssh的格式如下：
```
ssh [user@]hostname [command]
``` 
其中，user是远程服务器的用户名，hostname是远程服务器的主机名或IP地址，command是需要在远程服务器上执行的命令。如果省略了command，ssh将进入交互模式，允许用户在远程服务器上执行命令和操作。

2.docker
docker是一种开源的容器化平台，它允许开发者将应用程序及其依赖打包到一个轻量级的、可移植的容器中。通过docker，开发者可以在不同的环境中运行应用程序，而无需担心环境配置问题。docker使用操作系统级虚拟化技术，使得容器可以共享主机的内核资源，从而提高资源利用率和启动速度。docker还提供了丰富的工具和生态系统，如docker-compose、docker swarm和docker hub，帮助开发者更方便地管理和部署容器化应用程序。
docker的基本命令格式如下：
```
docker [command] [options] [arguments]
```
其中，command是docker的操作命令，如run、build、ps等，options是命令的选项参数，arguments是命令的参数，如容器名称、镜像名称等。通过组合不同的命令和选项，开发者可以实现容器的创建、管理、部署和监控等功能。

3.终端命令
终端命令是指在命令行界面（CLI）中输入的指令，用于与操作系统进行交互和执行各种任务。终端命令可以用于文件和目录管理、系统监控、网络配置、软件安装和卸载等操作。不同的操作系统可能有不同的终端命令集，但大多数命令在类Unix系统（如Linux和macOS）中是通用的。
常用的终端命令包括：
- `ls`：列出当前目录下的文件和子目录。
- `cd`：切换当前工作目录。
- `cat`：查看文件内容。
- `python`：运行Python解释器或执行Python脚本。
- `export`：设置或显示环境变量。


4.ai agent
ai agent是指一种具有自主决策和行动能力的智能代理，它可以感知环境、学习知识、制定策略并执行任务。ai agent通常由一个或多个智能体组成，每个智能体都有自己的感知、决策和行动模块。ai agent可以用于各种应用场景，如智能家居、智能交通、智能医疗等。
ai agent由系统工具（身体）和模型（大脑）组成，一些agent可以接入不同的模型如Claude-code可以调用deepseek、Kimi、甚至豆包api进行使用
但也有些ai agent只能使用特定的模型如Codex（GPTwork）只能使用GPT模型
常用的ai agent包括：Claudecode、Codex（GPT）、Trae（字节跳动）以及由智谱开发的GLM系列agent
claude code下载方法：
https://lcnaoyjp4e3z.feishu.cn/wiki/MtJlwX0B5iy6y9k5GZTcdjSknTd
给ai agent 配置mcp工具和skills可以让ai agent可以自动化的执行任务。
给ai agent配置更高的权限模式可以让它在执行任务时拥有更多的操作权限，从而提高其自主性和效率。但是，配置更高的权限模式也可能带来安全风险，因此需要谨慎操作，并确保ai agent的行为符合预期和安全规范。