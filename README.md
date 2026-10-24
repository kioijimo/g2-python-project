# g2-python-project

An equipment and inventory management system with built with Django

### Development Setup

1. Clone the repository and open it
2. Open a terminal and create a virtual environment and activate it and install the depencencies

```sh
python -m venv .venv
.venv/Scripts/activate.bat
pip install -r requirements.txt
```

3. Initialize the tailwind subapp inside

```sh
python manage.py tailwind init
```

4. Install the tailwind subapp dependencies

```sh
python manage.py tailwind install
```

5. Run migrations

```sh
python manage.py makemigrations && python manage.py migrate
```

6. Create the first administrator account

Only administrators can access the management area. Create one from the
command line:

```sh
python manage.py createadmin --email admin@example.com
```

The command prompts for the password twice. To promote an existing basic user
instead:

```sh
python manage.py createadmin --email user@example.com --promote
```

Administrator accounts cannot be created or promoted through the web portal.

7. Run the server with this

```sh
python manage.py tailwind dev
```
