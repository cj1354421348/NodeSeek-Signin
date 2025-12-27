---
description: Build and Run Docker Image Locally or via GitHub Actions
---

# Docker 构建与发布工作流

此工作流指导你如何构建 Docker 镜像，以及如何利用 GitHub Actions 自动发布镜像。

## 1. 本地构建与测试 (推荐)

在提交代码前，建议在本地测试构建。

```powershell
docker build -t nodeseek-signin .
```

运行容器测试 (确保 `.env` 文件存在):

```powershell
docker run --rm --env-file .env nodeseek-signin
```

## 2. 配置 GitHub 自动发布

我们已经创建了 `.github/workflows/docker-publish.yml`，并配置为**手动触发**。

### 步骤:

1.  **提交代码**:
    将代码推送到 GitHub。

2.  **手动触发构建**:
    - 进入 GitHub 仓库页面。
    - 点击顶部的 **Actions** 标签。
    - 在左侧选择 "Docker"。
    - 点击右侧的 **Run workflow** 按钮 (绿色)。
    - 选择分支 (通常是 `main`) 并点击 **Run workflow**。

3.  **获取镜像**:
    构建成功后，镜像将位于: `ghcr.io/<你的用户名>/nodeseek-signin:main`。 (TAG 取决于你构建时的 Git 引用，或者默认的 `main` / `latest`)

    拉取镜像:
    ```powershell
    docker pull ghcr.io/<你的用户名>/nodeseek-signin:main
    ```

## 3. 常见问题

- **权限问题**: 确保在 GitHub 仓库设置中 (Settings -> Actions -> General -> Workflow permissions)，选择了 "Read and write permissions"。
- **私有仓库**: 如果是私有仓库，拉取镜像时需要登录:
  `echo $CR_PAT | docker login ghcr.io -u <用户名> --password-stdin` (需要创建一个具有 `read:packages` 权限的 PAT)。
