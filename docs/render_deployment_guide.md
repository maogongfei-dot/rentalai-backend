# RentalAI Render Deployment Guide

## Backend（FastAPI）

**Render 类型：**
- Web Service

**启动命令：**

```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Python Version：**

```
python-3.11.9
```

**需要文件：**
- `requirements.txt`
- `runtime.txt`
- `Procfile`

---

## Frontend（React + Vite）

**Render 类型：**
- Static Site

**Build Command：**

```
npm install && npm run build
```

**Publish Directory：**

```
dist
```

**Root Directory：**

```
rental_app
```

---

## 当前数据库

**当前使用：**
- SQLite（仅开发环境）

**说明：**
后续正式上线建议升级 PostgreSQL。

---

## 当前状态

**已完成：**
- FastAPI
- SQLite
- SQLAlchemy
- React + Vite
- React Router
- API 联调
- 短租推荐系统
- 短租发布系统

---

## 后续建议

**下一阶段：**
- Render 正式部署
- PostgreSQL 升级
- 环境变量配置
- HTTPS 域名
- 用户系统
- 正式生产环境
