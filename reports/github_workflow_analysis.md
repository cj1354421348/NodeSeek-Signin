# GitHub Actions Cookie 回写与多账号机制分析

这份报告揭示了 `NodeSeek-Signin` 项目如何在无状态的 GitHub Actions 环境中实现状态持久化（Cookie 延续），以及它是如何在一个脚本中处理多组账号的。

## 1. 核心挑战：GitHub Actions 是无状态的

每次 GitHub Action 运行都是在一个全新的虚拟机容器中。脚本结束后，文件系统会被销毁。如果脚本更新了 Cookie，下次运行默认是拿不到的。

**解决方案**：利用 GitHub 的 **REST API** 修改仓库的 `Variables`（变量）。

> **注意**：这里用的是 Repository Variables，不是 Secrets。Secrets 是只读不可写的（对于 Action 脚本而言）。Variables 是明文可见且可写的。

## 2. Cookie 回写机制 (Persistence)

代码中实现了一个 `save_cookie_to_github_var` 函数，通过 HTTP 请求直接操作 GitHub API。

### 实现流程

1.  **权限准备**：
    *   需要一个 `GH_PAT` (Personal Access Token) 并在仓库 Secrets 中配置。
    *   **关键点**：默认的 `GITHUB_TOKEN` 只有仓库的读写权限，通常无法修改 Actions Variables。必须使用拥有 `repo` 权限的 PAT。

2.  **API 调用**：
    *   **接口**: `PATCH https://api.github.com/repos/{repo}/actions/variables/{var_name}`
    *   **动作**:
        *   先尝试 `PATCH` (更新)。
        *   如果返回 404 (变量不存在)，则尝试 `POST` (创建)。

3.  **代码骨架**：
    ```python
    def save_cookie_to_github_var(var_name, cookie_value):
        token = os.environ.get("GH_PAT")
        repo = os.environ.get("GITHUB_REPOSITORY") # 格式: username/repo
        
        url = f"https://api.github.com/repos/{repo}/actions/variables/{var_name}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        }
        
        # 尝试更新
        requests.patch(url, json={"name": var_name, "value": cookie_value}, headers=headers)
    ```

## 3. 多账号管理策略 (Multi-Account Strategy)

脚本采用了一种简单粗暴但有效的 **"分隔符 + 约定命名"** 策略来支持多账号。

### A. 配置输入 (Input)

它支持两种方式读取多账号：

1.  **主账号**：环境变量 `USER`, `PASS`
2.  **额外账号**：通过 `while` 循环动态读取 `USER1`/`PASS1`, `USER2`/`PASS2` ... 直到读不到为止。

```python
# 伪代码逻辑
accounts = []
# 读取主账号
if ENV["USER"]: accounts.append(ENV["USER"])

# 循环读取后续账号
index = 1
while True:
    u = ENV[f"USER{index}"]
    if not u: break
    accounts.append(u)
    index += 1
```

### B. Cookie 存储 (Storage)

虽然账号有多个，但 Cookie 只保存在**一个**变量 `NS_COOKIE` 中。

*   **数据结构**：字符串
*   **格式**：`cookie1 & cookie2 & cookie3`
*   **分隔符**：`&`

### C. 运行时的映射 (Runtime Mapping)

在运行时，脚本分别解析这两个列表：

*   `accounts` 列表: `[{u1,p1}, {u2,p2}, ...]`
*   `cookies` 列表: `NS_COOKIE.split('&')` -> `[c1, c2, ...]`

脚本通过**索引对齐** (Index Alignment) 来匹配账号和 Cookie。
`accounts[i]` 使用 `cookies[i]`。

> **潜在风险**：如果你在中间删除了一个账号，导致 `accounts` 变短，但 `NS_COOKIE` 没变，索引可能会错位。使用者必须小心维护。

### D. 批量保存 (Batch Save)

当所有账号任务执行完毕后，脚本会将所有（新的和旧的）Cookie 重新拼接：

```python
all_cookies_new = "&".join(cookie_list)
save_cookie("NS_COOKIE", all_cookies_new)
```

## 4. 总结：移植指南

如果你想在其他项目中复用这套机制：

1.  **Environment**: 确保你的 Actions yaml 注入了 `GH_PAT` 环境变量。
2.  **API**: 复制 `save_cookie_to_github_var` 函数。
3.  **Data Structure**: 使用分隔符（如 `&`, `|`, `;`）在一个变量里存所有 Session，避免创建 `COOKIE_USER1`, `COOKIE_USER2` 等几十个变量，那样会很难管理。
