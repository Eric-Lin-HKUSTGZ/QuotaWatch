# QuotaWatch

API 密钥额度监控仪表盘 - 一个用于监控多个平台 API 密钥余额的全栈应用程序。

## 技术栈

- **后端**: FastAPI (Python 3.10)
- **前端**: React + TypeScript + Vite
- **数据库**: PostgreSQL 15
- **缓存/队列**: Redis 7
- **ORM**: SQLModel
- **后台任务**: Arq
- **调度器**: APScheduler
- **UI 库**: Chakra UI
- **状态管理**: React Query (TanStack Query)

## 功能特性

- 🔐 使用 Fernet 加密安全存储 API 密钥
- 🔑 支持多个 API 提供商（OpenRouter、OpenAI 等）
- 📊 实时余额监控
- 📈 余额历史记录追踪
- 🔔 可配置的通知（邮件/Webhook）
- ⏰ 自动定期余额检查
- 🎨 现代化、响应式 UI

## 前置要求

- Docker 和 Docker Compose
- Python 3.10+（用于本地开发）
- Node.js 18+（用于本地开发）

## 快速开始

### 1. 克隆和设置

```bash
cd QuotaWatch
```

### 2. 环境变量

在根目录创建 `.env` 文件：

```env
# 加密密钥（必需 - 生成方式：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"）
MASTER_ENCRYPTION_KEY=your-encryption-key-here

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 数据库（默认配置适用于 docker-compose）
DATABASE_URL=postgresql://quotawatch:quotawatch_dev@db:5432/quotawatch

# Redis（默认配置适用于 docker-compose）
REDIS_URL=redis://cache:6379/0

# 邮件通知（可选）
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
```

### 3. 生成加密密钥

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

复制输出结果，并将其设置为 `.env` 文件中的 `MASTER_ENCRYPTION_KEY`。

### 4. 启动服务

```bash
docker-compose up -d
```

这将启动：
- PostgreSQL 数据库（端口 5432）
- Redis 缓存（端口 6379）
- FastAPI 后端（端口 8000）
- React 前端（端口 5173）

### 5. 运行后台工作进程

在另一个终端中，启动 Arq 工作进程：

```bash
cd backend
python run_worker.py
```

或使用 Docker：

```bash
docker-compose exec backend python run_worker.py
```

### 6. 访问应用

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 开发

### 后端开发

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### 数据库迁移

数据库表会在启动时自动创建。对于生产环境，建议使用 Alembic 进行迁移。

## API 端点

### 认证

- `POST /api/auth/register` - 注册新用户
- `POST /api/auth/login` - 登录并获取 JWT token
- `GET /api/auth/me` - 获取当前用户信息

### API 密钥

- `GET /api/keys` - 列出当前用户的所有 API 密钥
- `POST /api/keys` - 创建新的 API 密钥
- `POST /api/keys/test` - 测试 API 密钥（不保存）
- `POST /api/keys/{key_id}/trigger-check` - 手动触发余额检查
- `GET /api/keys/{key_id}/balance-history` - 获取余额历史记录
- `GET /api/platforms` - 获取所有可用的平台提供商

## 架构

### 适配器

系统使用适配器模式支持多个 API 提供商：

- `OpenRouterAdapter` - 从 OpenRouter API 获取余额
- `OpenAIUsageAdapter` - 从 OpenAI 使用数据估算余额

要添加新的提供商，请在 `backend/app/services/adapters/` 中创建新的适配器类，并在 `adapter_factory.py` 中注册。

### 安全

- 所有 API 密钥在存储前都使用 Fernet 对称加密进行加密
- 主加密密钥存储在环境变量中
- 使用 JWT token 进行身份验证
- 使用 bcrypt 进行密码哈希

### 后台任务

- 余额检查每 30 分钟运行一次（可配置）
- 使用 Arq 和 Redis 进行任务队列管理
- 当余额低于阈值时发送通知

## 项目结构

```
QuotaWatch/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routers/
│   │   │       ├── auth.py          # 认证路由
│   │   │       └── keys.py          # API 密钥路由
│   │   ├── core/
│   │   │   ├── database.py          # 数据库配置
│   │   │   └── security.py          # 安全服务（加密、JWT）
│   │   ├── models.py                # 数据模型
│   │   ├── services/
│   │   │   ├── adapters/            # API 提供商适配器
│   │   │   │   ├── base.py
│   │   │   │   ├── openrouter.py
│   │   │   │   └── openai.py
│   │   │   └── adapter_factory.py   # 适配器工厂
│   │   ├── worker.py                # Arq 后台任务
│   │   └── main.py                  # FastAPI 应用入口
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run_worker.py                # 工作进程启动脚本
│   └── seed_platforms.py            # 平台数据初始化脚本
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── BalanceDisplay.tsx   # 余额显示组件
│   │   ├── features/
│   │   │   └── Modals/
│   │   │       └── AddKeyModal.tsx  # 添加密钥模态框
│   │   ├── lib/
│   │   │   └── api.ts               # API 客户端和 React Query hooks
│   │   ├── App.tsx                  # 主应用组件
│   │   └── main.tsx                 # 应用入口
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml               # Docker Compose 配置
└── README.md
```

## 部署说明

### 生产环境注意事项

1. **加密密钥**: 确保 `MASTER_ENCRYPTION_KEY` 在生产环境中安全存储，不要提交到版本控制系统
2. **数据库**: 使用强密码，并配置适当的备份策略
3. **HTTPS**: 在生产环境中使用 HTTPS 保护 API 通信
4. **环境变量**: 所有敏感信息都应通过环境变量配置
5. **日志**: 配置适当的日志记录和监控

### 扩展性

- 可以通过添加新的适配器类轻松支持新的 API 提供商
- 后台任务使用 Redis 队列，可以水平扩展工作进程
- 数据库连接池可以根据负载进行调整

## 许可证

MIT
