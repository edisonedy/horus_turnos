# Despliegue HORUS Turnos

## 1. Subir a GitHub

No subas `.env`, tokens, logs, `.venv`, `media` ni `staticfiles`.

```powershell
git init
git add .
git commit -m "Initial HORUS Turnos"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/horus_turnos.git
git push -u origin main
```

## 2. Preparar servidor Ubuntu

Instalar dependencias:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql postgresql-contrib nginx git
```

Crear base de datos:

```bash
sudo -u postgres psql
CREATE DATABASE horus_turnos;
CREATE USER horus_turnos_user WITH PASSWORD 'CAMBIA_ESTE_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE horus_turnos TO horus_turnos_user;
\q
```

Clonar proyecto:

```bash
cd /var/www
sudo git clone https://github.com/TU_USUARIO/horus_turnos.git
sudo chown -R $USER:$USER /var/www/horus_turnos
cd /var/www/horus_turnos
```

Crear entorno:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crear `.env` en el servidor usando `.env.production.example`:

```bash
cp .env.production.example .env
nano .env
```

Ejecutar Django:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py check
```

## 3. Gunicorn systemd

Crear `/etc/systemd/system/horus-turnos.service`:

```ini
[Unit]
Description=HORUS Turnos Django
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/horus_turnos
EnvironmentFile=/var/www/horus_turnos/.env
ExecStart=/var/www/horus_turnos/.venv/bin/gunicorn horus_turnos.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo chown -R www-data:www-data /var/www/horus_turnos
sudo systemctl daemon-reload
sudo systemctl enable horus-turnos
sudo systemctl start horus-turnos
sudo systemctl status horus-turnos
```

## 4. Worker recordatorios

Crear `/etc/systemd/system/horus-recordatorios.service`:

```ini
[Unit]
Description=HORUS Turnos Recordatorios
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/horus_turnos
EnvironmentFile=/var/www/horus_turnos/.env
ExecStart=/var/www/horus_turnos/.venv/bin/python manage.py procesar_recordatorios_loop --intervalo 60
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable horus-recordatorios
sudo systemctl start horus-recordatorios
```

## 5. Nginx

Crear `/etc/nginx/sites-available/horus-turnos`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    location /static/ {
        alias /var/www/horus_turnos/staticfiles/;
    }

    location /media/ {
        alias /var/www/horus_turnos/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activar:

```bash
sudo ln -s /etc/nginx/sites-available/horus-turnos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6. SSL

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

## 7. Meta WhatsApp

En Meta configura:

```text
Callback URL: https://tu-dominio.com/whatsapp/webhook/
Verify token: el mismo WHATSAPP_VERIFY_TOKEN del .env
```

Luego en el panel:

```text
https://tu-dominio.com/panel/whatsapp/
```

Guarda:

```text
phone_number_id
business_account_id
access_token
verify_token
numero_whatsapp
activo=True
```
