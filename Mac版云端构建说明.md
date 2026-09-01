# 用 GitHub Actions 构建免安装的 macOS .app

## 为什么要这个

你现在手上的 `小红书多账号管理_Mac版.zip` 是「源码 + 一键脚本」：
对方双击后，**首次需要联网下载运行库（约 100MB，1-3 分钟）**，之后才能用。

如果想让对方拿到的是**真正的 `.app`，双击即用、完全不用装任何东西**，
就需要一台 Mac 来打包。没有 Mac 也没关系 —— GitHub 提供免费的 macOS 云机器。

> 原理：PyInstaller 不能交叉编译，Windows 上产不出 .app。
> GitHub Actions 的 `macos-13`（Intel）和 `macos-15`（Apple 芯片）是真实的 Mac 机器，
> 配置已经写好在 `.github/workflows/build-mac.yml`，直接跑就行。

---

## 你需要准备

1. 一个 GitHub 账号（免费，[github.com](https://github.com) 注册）
2. 电脑装了 Git（[git-scm.com](https://git-scm.com) 下载，一路下一步即可）
3. 本项目文件夹

仓库可以设为 **Private（私有）**，代码不会公开，免费账号也能用 Actions。

---

## 三步走

### 第 1 步：建仓库并推送代码

在 GitHub 网页上点右上角 `+` → `New repository`，
仓库名随意（如 `xhs-manager`），**不要勾选**任何初始化选项，点创建。

创建后会显示一个仓库地址，形如 `https://github.com/你的用户名/xhs-manager.git`。

然后在本项目文件夹里打开终端（Windows 用 Git Bash），依次执行：

```bash
cd "E:/CC/AI工作台/小红书多账号管理系统"        # 换成你的实际路径

git init
git add .
git commit -m "init"

git remote add origin https://github.com/你的用户名/xhs-manager.git
git branch -M main
git push -u origin main
```

> 如果提示输入账号密码：密码处要填 **Personal Access Token**（不是登录密码）。
> 获取方式：GitHub 网页 → 右上角头像 → Settings → Developer settings →
> Personal access tokens → Tokens (classic) → Generate new token，
> 勾上 `repo` 权限即可。

### 第 2 步：触发构建

打开仓库页面 → 上方 **Actions** 标签 → 左侧点「构建 macOS 应用」
→ 右侧 **Run workflow** → 点绿色按钮确认。

等约 **5-10 分钟**（苹果云机器比较慢），两个任务会并行跑完：

| 任务 | 产出 | 适用机器 |
|---|---|---|
| `intel` | `小红书多账号管理_macOS_intel.zip` | Intel 芯片的 Mac（2020 年前机型） |
| `apple-silicon` | `小红书多账号管理_macOS_apple-silicon.zip` | M1/M2/M3/M4 芯片（2020 年后机型） |

### 第 3 步：下载

任务变绿后点进去，页面最下方 **Artifacts** 区域即可下载。
每个 zip 约 200MB，解压得到 `小红书多账号管理.app`。

---

## 对方怎么用 .app

1. 解压 zip，把 `.app` 拖到「应用程序」文件夹（也可以直接双击）
2. **首次打开会被 macOS 拦**：右键（或 Control + 点击）→ 打开 → 再点「打开」
3. 之后双击即可正常运行

### 关于那个拦截提示

这是**没有做苹果公证**导致的（公证需要年费 688 元的开发者账号）。
不是文件损坏，右键打开一次就永久放行了。

如果嫌麻烦，可以花 688 元/年加入 Apple Developer 程序，用开发者 ID 签名 + 公证，
对方就完全无感。对于内部小范围分发，右键打开通常够用。

---

## 改代码后重新构建

```bash
git add .
git commit -m "更新说明"
git push
```

然后再去 Actions 点一次 Run workflow 即可。
也可以直接打标签自动构建并发布 Release：

```bash
git tag v6.6.1
git push origin v6.6.1
```

---

## 常见问题

**Q：Actions 按钮是灰的 / 找不到工作流？**
A：确认 `.github/workflows/build-mac.yml` 已经 push 上去了
（`git add .github` 别被 .gitignore 排除），并等 1-2 分钟刷新页面。

**Q：构建失败，日志里一堆红字？**
A：点进失败的任务看具体报错，最常见的是依赖版本问题。
把报错截图发开发者即可。

**Q：Intel 版能在 M 系列芯片上跑吗？**
A：能。M 系列有 Rosetta 2 转译层，可以运行 Intel 版，只是性能稍差。
不知道对方芯片就两个都发，让他挑；或者优先发 arm64 版。

**Q：免费账号的 Actions 有额度限制吗？**
A：私有仓库每月 2000 分钟，macOS 任务按 10 倍计费（即实际约 200 分钟）。
每次全量构建约 10-15 分钟（两个架构并行），完全够用。

---

## 附：本仓库与 Mac 一键包的关系

| 产物 | 面向 | 特点 |
|---|---|---|
| `dist/小红书多账号管理_Mac版.zip` | 直接发对方 | 对方需联网装一次运行库，体积小（40KB） |
| Actions 产出的 `.app` | 直接发对方 | 双击即用免安装，体积大（约 200MB） |
| `dist/小红书多账号管理.exe` | Windows 用户 | 单文件绿色版 |

三者功能完全一致，只是分发形态不同。
改了源码后记得重新执行 `python build/make_mac_zip.py` 刷新一键包。
