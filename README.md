# 📈 港美股市赚率 (PR) 自动化监控看板

基于 **GitHub Actions + GitHub Pages** 的全免费、零维护港美股市赚率（PR = PE / ROE / 100）自动化监控看板。

---

## 📁 包含文件

- [fetch_pr.py](file:///Users/apple/Downloads/未命名文件夹%2024/fetch_pr.py) : 港美股核心数据采集与市赚率（PR）计算脚本（基于 yfinance）。
- [index.html](file:///Users/apple/Downloads/未命名文件夹%2024/index.html) : 现代化自适应 Web 看板界面，支持实时筛选、排序与搜索。
- [.github/workflows/update.yml](file:///Users/apple/Downloads/未命名文件夹%2024/.github/workflows/update.yml) : GitHub Actions 自动化工作流配置（每天交易日收盘后自动同步并推送）。
- [requirements.txt](file:///Users/apple/Downloads/未命名文件夹%2024/requirements.txt) : Python 依赖包清单。

---

## 🚀 本地快速运行

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **手动拉取数据并计算**：
   ```bash
   python fetch_pr.py
   ```
   运行完成后，会在当前目录自动生成 `data.json`。

3. **查看网页**：
   直接双击打开 `index.html`，或使用任何本地静态服务器打开：
   ```bash
   python -m http.server 8000
   ```
   然后浏览器访问 `http://localhost:8000`。

---

## 🌐 免费全自动化部署（GitHub Pages）

1. **新建 GitHub 仓库**并将当前文件夹的所有代码推送（Push）上去：
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/你的用户名/你的仓库名.git
   git push -u origin main
   ```
2. **开启 GitHub Actions 写入权限**：
   - 仓库页面进入 **Settings -> Actions -> General -> Workflow permissions**。
   - 勾选 **Read and write permissions** 并保存。
3. **开启 GitHub Pages 网站服务**：
   - 仓库页面进入 **Settings -> Pages**。
   - 在 **Build and deployment** 下将 **Branch** 选为 `main` 分支、目录为 `/(root)`，点击 **Save**。
4. **效果**：
   - 以后每天收盘后 GitHub 会自动运行 Python 脚本抓取最新财报和股价，自动更新并部署。
   - 无论在电脑还是手机，打开 GitHub 提供的二级域名（如 `https://your-name.github.io/your-repo/`）即可随时查看最新市赚率！
