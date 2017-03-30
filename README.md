# **LinkedIn Scraper** #
http://34.197.99.99:8000

Login: linkedin
Pass: _adm1n_*

This tool was created for the search the company employees. You can add to the Search field the name of the company or LinkedIn ID. The result of the Search you can see on the Main page or it can be exported to the CSV format.
http://joxi.ru/brRp41OceoMk21
http://joxi.ru/Dr8O8XefX6jqA6



Linkedin parser is compatible with version Python 2: 2.6+
Used technologies: Django, Selenium, Celery
Used DB: PostgreSQL




# **The process of the Search** #
1. To enter the system you need to fill the login and password on the Login page 
(http://joxi.ru/KAgkNPQu4V7J5A)
2. After the authentication process user will be redirected to the main page of the project.
 http://joxi.ru/5md0yvwskK0MBm
 1/  As you can see at the screenshot, as the search request you can use 
  - the name of the company
  - LinkedIn ID of the company 
For example - 164735 is the ID of the company
https://www.linkedin.com/company-beta/164735/
 
   2/ Here is the Status of the search. It can look so:
      Complete (2)
      In progress (3)
      Problem with authentification with the LinkedIn profile (4)
      Error (Here we can have two types of the problems. You can reach the limit of      views for the LinkedIn profile. Also, you will get this status when the company with such ID doesn't exist.)

6/ This tab is showing the result on the search - you can check the result before to export it to the CSV.
7/ Button for saving the result and export this result to CSV format.

http://joxi.ru/82QDbOyhjZpo9m
When you click on the Search Details - you will be redirected to the Result page.
Here you can see:
- Company ID
- Employees of the company
- Title of Employees





# **Admin Page** #
http://34.197.99.99:8000/admin
Here you can edit settings and see the history of your actions with the LinkedIn Scraper

Search history:
http://34.197.99.99:8000/admin/inapp/linkedinsearchresult/
http://34.197.99.99:8000/admin/inapp/linkedinsearch/

http://joxi.ru/xAeJ7vPupZ5ELr
Here you can edit the history of the search (delete/edit)
To delete the search you need to select the search and press Delete it.

Changing of the the profile:

To change the LinkedIn profile that will be used for the search you need to go the link
http://34.197.99.99:8000/admin/inapp/linkedinuser/
You need to choose  > LinkedIn Users
http://joxi.ru/v294vX9f3ONaem
Here you can add/remove your LinkedIn profiles 
http://joxi.ru/BA0M81gtJNZ3Dr