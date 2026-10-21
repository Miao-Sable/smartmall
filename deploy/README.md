# SmartMall 部署指南

一条龙把项目部署到共享服务器：**前端静态托管 + 后端 Uvicorn + Nginx 反代**。

```
浏览器 ── HTTPS ──> Nginx ── /        ──> frontend/dist (静态文件)
                         └── /api/*   ──> Uvicorn (FastAPI) ──> PostgreSQL / SQLite
```

---

## 0. 快速启动（Docker Compose，推荐）

已提供容器化方案，一条命令在任意装有 Docker 的机器上启动整套（前端 Nginx + 后端 FastAPI + PostgreSQL）：

```bash
docker compose up -d --build
```

- 访问 http://localhost:8080（API 文档 http://localhost:8080/docs）
- 生产前在**项目根目录**建 `.env` 写入 `SECRET_KEY=<强随机值>`，compose 会自动读取；否则会落到 `change-me-in-production`
- 数据存在 Docker 卷 `pgdata` 里（PostgreSQL），重启不丢
- 相关文件：根目录 [docker-compose.yml](../docker-compose.yml)、[backend/Dockerfile](../backend/Dockerfile)、[frontend/Dockerfile](../frontend/Dockerfile)、[frontend/nginx.conf](../frontend/nginx.conf)

> 若想手动部署（Nginx + systemd + 自建 PostgreSQL/SQLite），继续往下看。

---

## 1. 前端构建

```bash
cd frontend
npm install
npm run build        # 实际执行：vue-tsc --noEmit && vite build
```

产出在 `frontend/dist/`，之后把 `dist/` 整个目录上传到服务器（例如 `/opt/smartmall/frontend/dist`）。

**API 地址（二选一）：**

- **同源部署（推荐）**：不设任何变量，前端默认用相对路径 `/api`，由 Nginx 反代到后端。本仓库的 [nginx.conf](./nginx.conf) 就是这种。
- **前后端分离**：在 `frontend/.env.production` 里写：
  ```bash
  VITE_API_BASE_URL=https://api.example.com
  ```
  （只有 `VITE_` 前缀的变量会打进前端包；改完要重新 `npm run build`。）

---

## 2. 后端部署

### 2.1 准备代码

把整个后端目录（`backend/`）和 **`mock/` 目录**一起上传（后端运行时要从 `mock/` 读商品/字典数据）。

### 2.2 配置环境变量

```bash
cd backend
cp ../deploy/.env.example .env   # 然后按 .env 里的注释逐项修改
```

重点必改：`SECRET_KEY`、`DEBUG=false`、`CORS_ORIGINS`（写成你前端的域名）。

### 2.3 建数据库（PostgreSQL 示例）

```sql
CREATE USER smartmall WITH PASSWORD 'yourpassword';
CREATE DATABASE smartmall OWNER smartmall;
```

（SQLite 则无需建库，启动时自动生成 `smartmall.db`。）

### 2.4 启动

```bash
cd backend
# SQLite：单 worker（避免并发写锁问题）
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# PostgreSQL：可多 worker
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

启动时会自动 `init_db()`：建表 + 灌入字典 + 建默认档案，**空库即可用**，无需手工建表。

### 2.5 用 systemd 常驻（推荐）

`/etc/systemd/system/smartmall.service`：

```ini
[Unit]
Description=SmartMall API
After=network.target

[Service]
WorkingDirectory=/opt/smartmall/backend
ExecStart=/opt/smartmall/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
EnvironmentFile=/opt/smartmall/backend/.env
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now smartmall
systemctl status smartmall
```

---

## 3. Nginx

```bash
cp deploy/nginx.conf /etc/nginx/conf.d/smartmall.conf
# 编辑：改 server_name 与 root（指向你上传的 dist 目录）
nginx -t && systemctl reload nginx
```

---

## 4. HTTPS（certbot）

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d smartmall.example.com
```

签发后把 80 端口改成 301 跳转到 https，启用 [nginx.conf](./nginx.conf) 里注释好的 443 段即可。

---

## 5. 部署后验证清单

- [ ] `curl https://你的域名/api/health` → `{"status":"ok",...}`
- [ ] 浏览器打开首页能加载、能注册/登录
- [ ] 扫码/购物清单/社区评价各走一遍
- [ ] 换个账号登录，确认看不到对方账号的扫描历史（数据隔离）
- [ ] `/docs` 能打开（可选，若不需要可在 Nginx 里删掉对应 location）

---

## 6. 注意事项

- **SECRET_KEY 必须改**：默认值是开发用的，不改等于把登录态钥匙公开。
- **mock/ 目录要一起部署**，否则后端找不到商品会 500/404。
- **SQLite 用单 worker**；多 worker 请切 PostgreSQL。
- 目前**没有数据库迁移工具（Alembic）**，首次部署没问题；后续改表结构建议先补上 Alembic 再迭代。
- 社区评价是**公开可见**的（按设计）；扫描历史/家庭档案按账号隔离。
