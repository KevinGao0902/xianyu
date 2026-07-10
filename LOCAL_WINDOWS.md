# Windows 本地运行

本项目已使用 Python 3.11 创建独立环境：

```text
D:\workspace-my\AI\xianyu-auto-reply-fix\.venv\Scripts\python.exe
```

## 启动

双击 `start-local.cmd`，或在项目目录运行：

```powershell
.\.venv\Scripts\python.exe Start.py
```

访问地址：

- 管理页面：`http://127.0.0.1:8090`
- API 文档：`http://127.0.0.1:8090/docs`
- 健康检查：`http://127.0.0.1:8090/health`

## PyCharm

1. 打开 Settings > Project > Python Interpreter。
2. 选择 Existing environment。
3. 解释器选择 `.venv\Scripts\python.exe`。
4. 新建 Python 运行配置，脚本选择 `Start.py`，工作目录选择项目根目录。

首次登录后立即修改默认管理员密码。闲鱼账号、聊天、订单、发布和自动发货配置都在该管理页面完成。
