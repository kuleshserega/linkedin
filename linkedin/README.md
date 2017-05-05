LINKEDIN PARSER:

Used technologies: Django, Selenium, Celery
Used DB: PostgreSQL

Need to add restart searches with connection refused into cron tasks. Example:
    * */1 * * * user /home/user/public_html/INPROJ/.env/bin/python manage.py restart_task_with_connection_refused
