# AGIR OBRAS

Sistema de Monitoramento de Obras.

## Rodando com PostgreSQL

1) Instale as dependências:

`pip install -r requirements.txt`

2) Suba um PostgreSQL (opção com Docker):

`docker compose up -d`

3) Crie um arquivo `.env` (baseie-se no `.env.example`) e configure o banco.

4) Rode as migrações e inicie o servidor:

`python manage.py migrate`

`python manage.py runserver`

## Variáveis de ambiente do banco

Você pode configurar de 2 formas:

- **`DATABASE_URL`** (recomendado): 
  -`postgresql://usuario:senha@host:5432/nome_do_banco`
- **Env vars separadas**:
  - `DB_ENGINE=postgres`
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

## Cloudinary (mídia)

Para salvar e servir uploads (imagens/arquivos) via Cloudinary, configure no `.env`:

- `CLOUDINARY_ENABLED=true`
- `CLOUDINARY_CLOUD_NAME=...`
- `CLOUDINARY_API_KEY=...`
- `CLOUDINARY_API_SECRET=...`

## Deploy (Render + Neon + Cloudinary)

### 1) Neon (PostgreSQL)

- Crie um banco no Neon e copie a connection string.
- No Render (ou no ambiente), configure `DATABASE_URL` (recomendado) com SSL, por exemplo:
  - `postgresql://usuario:senha@host:5432/nome_do_banco?sslmode=require`

### 2) Render (Django)

- Opção A (recomendado): use o blueprint `render.yaml` deste repositório.
- Opção B: crie um **Web Service** no Render apontando para o repositório e configure:
  - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
  - **Start Command**: `gunicorn app.wsgi:application`

### 3) Variáveis de ambiente no Render

- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY=...` (obrigatório em produção)
- `DJANGO_ALLOWED_HOSTS=seu-app.onrender.com,seu-dominio.com`
- `DATABASE_URL=...` (Neon, com `sslmode=require`)
- Cloudinary:
  - `CLOUDINARY_ENABLED=true`
  - `CLOUDINARY_CLOUD_NAME=...`
  - `CLOUDINARY_API_KEY=...`
  - `CLOUDINARY_API_SECRET=...`
- Se você receber erro de CSRF no admin/login, configure:
  - `DJANGO_CSRF_TRUSTED_ORIGINS=https://seu-app.onrender.com`
