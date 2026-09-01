# 小红书多账号登录管理系统

> 小红书 PC 端多账号集中管理工具 · 100% 纯人工 · 合规轻量 · 单文件 EXE

一个基于 PyQt6 / QtWebEngine 内嵌 Chromium 的桌面客户端，把多个小红书账号的登录态与常用后台集中在一个窗口里管理。每个账号拥有独立的浏览器配置（独立 Cookie / 缓存目录），同账号多平台一次登录全互通，不同账号之间严格隔离、绝不串号。

适配 **5–20 个账号**的中小矩阵人工运营场景，全程**零自动化、零抓取、零批量托管**，所有登录与发布操作均由人工手动完成，符合小红书平台合规要求。

## ✨ 功能特性

- **单窗口集中管理**：左侧账号树 + 右侧内嵌浏览器，切换账号 / 平台就地打开，不弹多窗口。
- **账号隔离**：每个账号一个 `QWebEngineProfile`（独立存储目录 + 强制持久 Cookie），从根源规避同设备账号关联风控。
- **六大小红书官方 PC 后台一键跳转**：兴趣社区、创作服务平台、专业号后台、千帆、聚光、预留拓展端口。
- **同账号多平台互通**：同一账号在各后台一次登录，全平台共享登录态。
- **设置与备份**：硬件加速开关（自动探测独显）、数据备份与恢复。
- **跨平台**：Windows 单文件 EXE；macOS 版通过 GitHub Actions 自动打包 `.app`。
- **静态演示**：`demo/` 提供无需登录即可体验完整界面的交互演示页。

## 🧱 技术架构

- **语言 / 框架**：Python 3.13 + PyQt6 + PyQt6-WebEngine（内嵌 Chromium）
- **打包**：PyInstaller 单文件 EXE
- **数据目录**：
  - Windows：`%APPDATA%/XHSManager`
  - macOS：`~/Library/Application Support/XHSManager`
- **账号上限**：强制 20 个（聚焦中小矩阵，轻量化架构）

## 📁 目录结构

```
.
├── src/                  # 应用源码（入口 main.py / config / settings / store / theme / icons / assets）
├── demo/                 # 静态交互演示（双击 HTML 即可体验界面）
├── build/                # PyInstaller spec 与 macOS 打包脚本（entitlements.plist / make_mac_zip.py）
├── .github/workflows/    # macOS 自动构建工作流（打 v* 标签触发）
├── requirements.txt      # Python 依赖
├── deploy.bat / deploy.ps1
└── Mac版云端构建说明.md
```

## 🛠 构建与运行

### Windows

```bash
pip install -r requirements.txt
python -m PyInstaller --noconfirm build/xhs_manager.spec
```

产物为单文件 EXE，绿色免安装，可直接复制到其它机器运行。

### macOS

方式一（自动）：在仓库打一个版本标签即可触发 GitHub Actions 自动打包：

```bash
git tag v6.6.0
git push origin v6.6.0
```

方式二（本地）：

```bash
python -m PyInstaller build/xhs_manager_mac.spec
```

## ⚠️ 合规声明

本工具**仅提供浏览器级别的账号集中管理与页面唤起能力**，明确不包含任何自动化、脚本化、批量托管行为：

- 无任何自动发文、自动互动、自动审核、自动定时执行功能；
- 无内容自动检测 / 修改 / 拦截，违禁词仅作静态查询参考；
- 所有账号操作、内容处理、数据查看均由人工手动触发。

请在使用过程中遵守小红书平台规则，合规运营。

## 📄 License

未声明许可证，保留所有权利。当前仅供个人学习与交流使用；如需开源或商业使用，请联系作者补充许可证。

---

*本项目为个人运营辅助工具，与小红书官方无隶属关系。*
