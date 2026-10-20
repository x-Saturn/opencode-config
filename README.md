# OpenCode 配置同步仓库

在多台设备之间同步 OpenCode 的全局配置和 TUI 设置。配置目录本身就是一个 Git 仓库。

- 仓库地址：https://github.com/x-Saturn/opencode-config
- Windows 路径：`%USERPROFILE%\.config\opencode`
- macOS / Linux 路径：`~/.config/opencode`

在新设备上，把这个地址交给该设备的 OpenCode 让它自己操作即可：

```text
https://raw.githubusercontent.com/x-Saturn/opencode-config/main/README.md
```

让它读取本文件并执行「新设备初始化」一节。

## 同步范围

纳入版本控制：

| 内容 | 说明 |
| --- | --- |
| `opencode.jsonc` | 服务端配置：默认模型、providers、MCP、agents、permissions、references 等 |
| `cli.json` | TUI 设置：主题、键位、会话展示、通知、diff 等 |
| `agents/` `commands/` `skills/` `plugins/` `themes/` | 自定义 agent、斜杠命令、skill、插件、主题（存在时自动跟踪） |
| `package.json` / `package-lock.json` | 全局插件依赖声明 |

明确**不**同步：

- `service.json`：本机后台服务注册信息（端口、认证令牌），换机必须重新生成。
- `node_modules/`：依赖目录，在新设备用 `npm ci` 还原。
- `~/.local/share/opencode/`：`opencode.db`（会话历史，可能上百 MB）、`log/`、`snapshot/`、`tool-output/`。
- `~/.local/state/opencode/`：`service.json`、`model.json`、`prompt-history.jsonl`、`frecency.jsonl`，属于本机状态。

## 新设备初始化

> 这一节是写给新设备上的 OpenCode 执行的：把本文件的 URL 交给它，让它按步骤操作即可。

1. 安装 OpenCode 并确认可运行：

   ```bash
   opencode --version
   ```

2. 停掉后台服务：

   ```bash
   opencode service stop
   ```

3. 备份已存在的配置目录（首次启动会自动创建该目录）：

   ```powershell
   # Windows
   Rename-Item "$HOME\.config\opencode" "opencode.bak"
   ```

   ```bash
   # macOS / Linux
   mv ~/.config/opencode ~/.config/opencode.bak
   ```

4. 克隆本仓库到配置目录：

   ```bash
   git clone https://github.com/x-Saturn/opencode-config.git ~/.config/opencode
   ```

   Windows 目标路径写 `"$HOME\.config\opencode"`。

5. 还原插件依赖（存在 `package.json` 时执行）：

   ```bash
   cd ~/.config/opencode && npm ci
   ```

6. 重启服务并验证：

   ```bash
   opencode service restart
   opencode api get /api/info
   ```

7. 重新连接凭据。**凭据不随仓库迁移**，它们保存在本机服务侧：

   - `/connect`：逐个登录 provider（API key 或 OAuth）
   - `/mcps`：重新授权需要 OAuth 的 MCP server

8. 确认 `opencode mcp list` 状态正常，并在 `/models` 里检查默认模型是否可用。

## 日常同步

改动一端后：

```bash
cd ~/.config/opencode
git add -A
git commit -m "config: <说明>"
git pull --rebase   # 推送前先吸收另一端的改动
git push
```

另一端拉取：

```bash
cd ~/.config/opencode
git pull
opencode service restart
```

`cli.json` 会热加载，`opencode.jsonc` 改动后重启后台服务最稳妥。

## 安全规则

- 本仓库是**公开**仓库，只放非敏感配置。需要改为私有：`gh repo edit --visibility private`（改私有后新设备必须认证才能 clone、也无法直接抓取 README）。
- 仓库里**不放明文密钥**。需要凭据时用变量替换：
  - `{env:OPENAI_API_KEY}`：读环境变量
  - `{file:~/.secrets/openai-key}`：读本机文件，文件本身不进仓库
- 提交前自查暂存区：

  ```bash
  git diff --cached | grep -Ei 'sk-|api[_-]?key|token|secret|password'
  ```

- `service.json`、`*.db`、日志、快照、`node_modules/` 永远不提交。

## 关于项目级配置

每个项目自己的 `opencode.jsonc` 或 `.opencode/` 应该跟项目仓库走，不放进本仓库。写入其中的密钥同样要用 `{env:...}` / `{file:...}` 引用。

## 故障排查

- 服务起不来：`opencode service status` → `opencode service restart`；仍异常时用 `opencode --standalone` 对照，隔离共享服务问题。
- 配置没生效：确认文件确实在 `~/.config/opencode/`，并检查是否被更近的项目级配置（`opencode.jsonc`、`.opencode/opencode.jsonc`）覆盖。
- 模型不可用：凭据不会随仓库同步，重新 `/connect` 后 `/models` 选择。
- MCP 显示未授权：`/mcps` 里对该 server 重新登录，状态确认已连接前都算未完成。
- 日志位置：`~/.local/share/opencode/log/opencode.log`，`role=server` 可看服务端问题。
