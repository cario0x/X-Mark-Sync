# X-Mark Sync

**X-Mark Sync** 是一款自动化的 Twitter (X) 书签同步工具。它使用 Playwright 模拟浏览器登录，抓取您的书签，并将其保存为 Obsidian 友好的 Markdown 文件。

## 功能特点
- 🔐 **安全登录**：本地浏览器模拟登录，Cookie 仅保存在本地。
- 🔄 **自动抓取**：自动滚动加载书签页面。
- 📝 **Markdown 导出**：生成带有 YAML Frontmatter 的 Markdown 文件，支持 Obsidian Dataview。
- 📂 **分类管理**：支持根据 Twitter 书签文件夹（如有）或自定义规则进行分类。

## 环境要求
- Python 3.10+
- Node.js (Playwright 依赖)

## 快速开始

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd X-Mark-Sync
```

### 2. 创建虚拟环境
建议使用虚拟环境以避免依赖冲突：
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. 运行
(待开发完成后补充)
```bash
python src/main.py
```

## 目录结构
```
X-Mark Sync/
├── config/         # 配置文件
├── data/           # 本地数据存储 (Obsidian Vault 路径)
├── src/            # 源代码
│   ├── auth.py     # 登录模块
│   ├── scraper.py  # 抓取模块
│   ├── parser.py   # 解析模块
│   └── storage.py  # 存储模块
├── requirements.txt
└── README.md
```

