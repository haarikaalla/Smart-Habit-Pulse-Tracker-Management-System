# Smart-Habit-Pulse-Tracker-Management-System
# Smart Habit Pulse Tracker Management System

A full-stack web application built using Django that helps users track, manage, and monitor their daily habits efficiently. The system supports real-time updates using AJAX and follows RESTful API principles.

##  Features

- Add new habits
-  View all habits dynamically
-  Mark habits as completed
- Delete habits
- Real-time updates using AJAX (no page reload)
- Timestamp tracking for each habit
- Responsive UI using Bootstrap

##  Technologies Used

### Frontend
- HTML
- CSS
- Bootstrap
- JavaScript
- jQuery
- AJAX

### Backend
- Python
- Django Framework

### Database
- MySQL (Configured)
- Django ORM

### API
- RESTful API implementation using Django views

## Project Structure
habitpulse/
│
├── tracker/
│ ├── migrations/
│ ├── templates/
│ │ └── index.html
│ ├── models.py
│ ├── views.py
│ ├── urls.py
│
├── habitpulse/
│ ├── settings.py
│ ├── urls.py
│
├── manage.py
└── README.md

 Setup Instructions

### 1️)Clone the Repository


git clone https://github.com/haarikaalla/Smart-Habit-Pulse-Tracker-Management-System.git

cd Smart-Habit-Pulse-Tracker-Management-System


### 2️) Create Virtual Environment


python -m venv venv
venv\Scripts\activate (Windows)


### 3️)Install Dependencies

pip install django mysqlclient

### 4️) Configure MySQL Database

Update `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'habitpulse_db',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
5️) Run Migrations
python manage.py makemigrations
python manage.py migrate
6️) Run Server
python manage.py runserver

Open in browser:
 http://127.0.0.1:8000/
