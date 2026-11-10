# Jolo

A modern social platform backend built with Django and Django REST Framework. This project powers user authentication, social feeds, messaging, creator monetization, moderation, and community engagement features for a premium digital platform.

## Overview

Jolo is designed as a scalable backend for a social and creator-focused application. It includes API endpoints for:

- User account creation and authentication
- Public and private profile management
- Feed creation, likes, comments, unlocks, and reports
- Follow/follower relationships and suggested friends
- Stories and social interactions
- Real-time messaging and online presence tracking
- Creator monetization and Stripe payouts
- Notifications and content moderation
- CMS pages and support/legal content

## Tech Stack

- Python 3.11+
- Django 5.2
- Django REST Framework
- Django Channels
- Redis
- JWT Authentication
- SQLite (default for local development)
- Cloudinary for media hosting
- Stripe for payments and payouts
- drf-spectacular for API schema/docs

## Project Structure

```text
jolo/
├── apps/
│   ├── account/
│   ├── cms/
│   ├── feed/
│   ├── messaging/
│   ├── moderation/
│   ├── monetization/
│   └── notification/
├── api/
│   └── v1/
├── project/
├── staticfiles/
├── db.sqlite3
├── manage.py
├── requirements.txt
├── README.md
├── TESTING_GUIDE.md
├── API_ENDPOINTS.md
└── verify_suggestions.py
```

## Main Features

### Account & Profiles
- Signup/login/logout flows
- JWT-based authentication
- Password reset and OTP-based recovery
- Public profile endpoints
- User status and account management

### Feed & Social Discovery
- Create and view feed posts
- Like and comment interactions
- Post locking/unlocking with paid access
- Following and unfollowing users
- Suggested friends based on activity scoring
- Block and mute controls
- Post reporting and moderation

### Messaging & Real-Time Features
- One-to-one chat sessions
- Message reactions and translation support
- Real-time online status tracking
- WebSocket-based messaging infrastructure

### Monetization
- Creator monetization application
- Stripe checkout and webhooks
- Payout account management
- Creator vault and payout eligibility

### Moderation & Safety
- Text and visual moderation hooks
- Violation log tracking
- User/content reporting workflows
- Safety and support CMS pages

## Prerequisites

Before running this project locally, make sure you have:

- Python 3.11 or newer
- pip installed
- Redis running locally on port 6379
- Git
- Virtual environment support

## Installation

1. Clone the repository:

```bash
git clone https://github.com/shourav98/jolo.git
cd jolo
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables (recommended):

Create a `.env` file in the project root with values like:

```env
HIVE_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
```

5. Apply database migrations:

```bash
python manage.py migrate
```

6. Run the development server:

```bash
python manage.py runserver
```

Optional: start Redis if it is not already running.

## Running the Project

The project runs by default at:

```text
http://127.0.0.1:8000/
```

### API Documentation

- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`

## Default Admin

Django admin is available at:

```text
http://127.0.0.1:8000/admin/
```

## Useful Commands

```bash
# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run tests
python manage.py test

# Collect static files for production
python manage.py collectstatic
```

## Notes

- The project uses SQLite by default for local development.
- Redis is required for Channels WebSocket support and real-time updates.
- `DEBUG` is currently enabled in `project/settings.py` for development convenience.
- For production deployment, configure secure environment variables and disable debug mode.

## Contribution

Contributions are welcome. Please fork the repository, create a feature branch, and submit a pull request with a clear description of your changes.

## Contact

For questions or collaboration opportunities, contact the project owner through the GitHub repository or project maintainers.
