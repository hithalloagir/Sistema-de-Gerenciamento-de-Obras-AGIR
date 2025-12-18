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
