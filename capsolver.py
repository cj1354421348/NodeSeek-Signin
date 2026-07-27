from curl_cffi import requests
import time
from typing import Optional

class CapSolverError(Exception):
    """CapSolver 解决器错误基类"""
    pass

class CapSolver:
    """
    CapSolver 验证码解决工具
    
    使用 CapSolver API 解决 Turnstile 验证码，获取验证令牌
    参考文档: https://docs.capsolver.com/guide/captcha/cloudflare_turnstile.html
    """
    
    def __init__(
        self, 
        api_base_url: str = "https://api.capsolver.com",
        client_key: str = "",
        max_retries: int = 20,
        retry_interval: int = 3,
        timeout: int = 60
    ):
        self.api_base_url = api_base_url or "https://api.capsolver.com"
        self.create_task_url = f"{self.api_base_url}/createTask"
        self.get_result_url = f"{self.api_base_url}/getTaskResult"
        self.client_key = client_key
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.timeout = timeout
    
    def solve(
        self,
        url: str,
        sitekey: str,
        user_agent: Optional[str] = None,
        verbose: bool = False
    ) -> str:
        if verbose:
            print("正在创建 CapSolver 验证任务...")
            
        task_id = self._create_task(url, sitekey, user_agent, verbose)
        if not task_id:
            raise CapSolverError("创建 CapSolver 验证码任务失败")
            
        token = self._get_task_result(task_id, verbose)
        if not token:
            raise CapSolverError("获取 CapSolver 验证码结果失败")
            
        if verbose:
            print(f"CapSolver 验证码解决成功: {token[:30]}...{token[-10:] if len(token) > 30 else ''}")
            
        return token
        
    def _create_task(
        self,
        url: str,
        sitekey: str,
        user_agent: Optional[str] = None,
        verbose: bool = False
    ) -> Optional[str]:
        data = {
            "clientKey": self.client_key,
            "task": {
                "type": "AntiTurnstileTaskProxyLess",
                "websiteURL": url,
                "websiteKey": sitekey
            }
        }
        
        if user_agent:
            data["task"]["userAgent"] = user_agent
            
        try:
            response = requests.post(
                self.create_task_url, 
                json=data,
                timeout=self.timeout,
                impersonate="chrome110"
            )
            result = response.json()
            
            if result.get("errorId") == 0:
                task_id = result.get("taskId")
                if verbose:
                    print(f"CapSolver 成功创建任务，ID: {task_id}")
                return task_id
            else:
                error_desc = result.get('errorDescription', '未知错误')
                if verbose:
                    print(f"CapSolver 创建任务失败: {error_desc}")
                return None
                
        except Exception as e:
            if verbose:
                print(f"CapSolver 创建任务过程中发生异常: {e}")
            return None
    
    def _get_task_result(self, task_id: str, verbose: bool = False) -> Optional[str]:
        data = {
            "clientKey": self.client_key,
            "taskId": task_id
        }
        
        for attempt in range(1, self.max_retries + 1):
            try:
                if verbose:
                    print(f"尝试获取 CapSolver 任务结果 ({attempt}/{self.max_retries})...")
                    
                response = requests.post(
                    self.get_result_url,
                    json=data,
                    timeout=self.timeout,
                    impersonate="chrome110"
                )
                result = response.json()
                
                if result.get("errorId", 0) > 0:
                    error_desc = result.get('errorDescription', '未知错误')
                    if verbose:
                        print(f"CapSolver 获取结果失败: {error_desc}")
                    return None
                
                status = result.get("status")
                
                if status == "ready":
                    token = result.get("solution", {}).get("token")
                    if verbose:
                        print("CapSolver 任务已完成")
                    return token
                
                elif status == "processing":
                    if verbose:
                        print(f"CapSolver 任务处理中，等待 {self.retry_interval} 秒后重试...")
                    time.sleep(self.retry_interval)
                    continue
                    
            except Exception as e:
                if verbose:
                    print(f"CapSolver 获取任务结果异常: {e}")
                return None
                
        if verbose:
            print("CapSolver 获取任务结果超时")
        return None
