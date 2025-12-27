# Cloudflare Turnstile 通用解决方案架构报告

这份报告提炼了 `NodeSeek-Signin` 项目中通过 Cloudflare 验证的核心技术方案。你可以按照此指南将相同的逻辑移植到任何需要自动化绕过 Cloudflare 的 Python 程序中。

## 核心战术：双层突破

要骗过 Cloudflare，必须同时解决两个层面的问题：**网络指纹** 和 **业务验证**。缺一不可。

### 第一层：网络指纹伪装 (TLS Fingerprinting)

**问题**：
标准的 Python `requests` 库发出的 TLS (SSL) 握手包特征非常明显，Cloudflare 会在 HTTP 连接建立阶段直接识别出你是脚本，从而拒绝服务或无限循环验证码。

**解决方案**：
使用 `curl_cffi` 库替代 `requests`。

**关键代码提取**：
```python
from curl_cffi import requests

# 核心魔法：impersonate参数
# 这会让你的 Python 脚本发出完全模拟真实 Chrome 浏览器的 TLS 握手包
# 推荐版本：chrome110, chrome120, chrome136 (越新越好，但要稳定)
session = requests.Session(impersonate="chrome136")

# 之后的请求完全兼容 requests 的用法
response = session.get("https://target-website.com")
```

**移植指南**：
在你的新程序中，凡是涉及与 Cloudflare 保护的接口交互的地方，**必须**使用 `curl_cffi` 的 `requests` 接口，并带上 `impersonate` 参数。不要混用标准 `requests` 库。

---

### 第二层：交互式验证 (Turnstile Challenge)

**问题**： 
登录或提交表单时，Cloudflare 要求提供一个 `token` (通常在表单字段 `cf-turnstile-response` 或类似的字段中)。这个 Token 是浏览器运行一段复杂的 JavaScript 代码后生成的。

**解决方案**：
**云端代打（API Outsourcing）**。不要尝试在本地用 Selenium/Puppeteer 去模拟（效率低且容易被检测），直接把验证参数发给专业的打码平台，拿回 Token。

**实现流程**：

1.  **准备阶段**：
    *   **SiteKey**: 在目标网页源码中搜索 `sitekey`。通常在 `div` 标签里，例如 `<div class="cf-turnstile" data-sitekey="0x4AAAAAAA...">`。
    *   **PageUrl**: 触发验证的页面 URL。

2.  **调用打码 API**：
    构造请求发送给打码平台（例如 YesCaptcha, CapSolver, 2Captcha 等）。
    *   **输入**: `TargetWebsiteURL`, `SiteKey`, `TaskType` (通常是 `TurnstileTaskProxyless`)。

3.  **获取 Token**：
    API 会返回一串加密字符串（如 `0.4uHq...`）。

4.  **注入请求**：
    在你的业务请求（如登录 POST）中，携带这个 Token。

**通用代码模板**：

```python
import time
import json
from curl_cffi import requests

def solve_turnstile(website_url, site_key):
    """
    通用 Turnstile 解决函数
    需要替换下面的 API 地址和 KEY 为你使用的打码平台
    """
    # 1. 创建任务
    create_task_url = "https://api.captcha-service.com/createTask"
    payload = {
        "clientKey": "YOUR_API_KEY",
        "task": {
            "type": "TurnstileTaskProxyless",
            "websiteURL": website_url,
            "websiteKey": site_key
        }
    }
    
    # 使用 requests 发送也没问题，因为打码平台没有 CF 防护
    resp = requests.post(create_task_url, json=payload).json()
    task_id = resp.get("taskId")
    
    if not task_id:
        raise Exception("创建打码任务失败")
        
    print(f"任务创建成功: {task_id}，等待处理...")
    
    # 2. 轮询结果
    get_result_url = "https://api.captcha-service.com/getTaskResult"
    for _ in range(20):
        time.sleep(3) # 等待几秒
        resp = requests.post(get_result_url, json={
            "clientKey": "YOUR_API_KEY",
            "taskId": task_id
        }).json()
        
        status = resp.get("status")
        if status == "ready":
             # 拿到 Token！
            token = resp.get("solution", {}).get("token")
            return token
            
    raise Exception("等待打码结果超时")

# --- 集成示例 ---

# 1. 目标网站信息
TARGET_URL = "https://www.nodeseek.com/signIn.html"
SITE_KEY = "0x4AAAAAAAaNy7leGjewpVyR" # 必须从目标网站 HTML 中提取

# 2. 获取 Token (这一步可能需要几秒到十几秒)
token = solve_turnstile(TARGET_URL, SITE_KEY)
print(f"获取到 Token: {token[:20]}...")

# 3. 带 Token 提交业务请求 (必须用 curl_cffi)
session = requests.Session(impersonate="chrome136")

login_payload = {
    "username": "my_user",
    "password": "my_password",
    "token": token,  # <--- 关键注入点：这里把买来的 Token 塞进去
    "source": "turnstile" # 有些网站可能需要额外的标识字段
}

resp = session.post(
    "https://www.nodeseek.com/api/account/signIn", 
    json=login_payload,
    headers={"User-Agent": "Mozilla/5.0 ..."} # 最好也带上真实 UA
)

print(resp.text)
```

## 总结

要在其他程序中复刻此方案，你只需要：

1.  **依赖库**: 安装 `curl_cffi`。
2.  **账号**: 注册一个支持 Turnstile 的打码平台账号（YesCaptcha, 2Captcha 等）。
3.  **信息收集**: 去目标网站 F12 找到 `data-sitekey`。
4.  **代码集成**: 复制上面的模板，替换 API Key 和 URL。

这就是目前最稳健的"过盾"方案。不要试图去自己写算法算 Turnstile，那是数学家做的事，工程师只需要五块钱买一万次 API 调用。
