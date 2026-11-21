run:
	@./manage.py runserver 0.0.0.0:8000
migrate:
	@./manage.py migrate
makemigrations:
	@./manage.py makemigrations