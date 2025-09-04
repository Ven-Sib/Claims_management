# Claims Management System

A Django-based web application for managing insurance claims with features for claim tracking, notes, flagging, and reporting. Built with modern web technologies including HTMX for dynamic interactions and Bootstrap for responsive design. https://claims-management-mhb2.onrender.com

## Features

- **Claims Dashboard** - Paginated list of all insurance claims with search and filtering
- **Claim Details Modal** - Detailed view with notes, actions, and status tracking
- **Search & Filter** - Real-time search by claim ID, patient name, insurer, or status
- **Flag System** - Mark claims for review with visual indicators
- **Notes System** - Add admin, system, or user notes to claims
- **Report Generation** - Generate detailed claim reports
- **User Profiles** - Profile management with picture uploads
- **Responsive Design** - Mobile-friendly interface with horizontal scrolling tables
- **Real-time Updates** - HTMX-powered dynamic content loading

## Tech Stack

- **Backend**: Django 4.2.23, Python 3.11+
- **Frontend**: Bootstrap 5.3, HTMX, Alpine.js
- **Database**: SQLite (production ready)
- **Deployment**: Render.com with automatic GitHub integration
- **Static Files**: WhiteNoise for serving CSS/JS/images
- **Media Files**: Custom middleware for user uploads

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Git
- Virtual environment (recommended)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/Ven-Sib/Claims_management.git
cd Claims_management
```

2. **Create and activate virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
# Windows
set DEBUG=True

# macOS/Linux
export DEBUG=True
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser (optional)**
```bash
python manage.py createsuperuser
```

7. **Collect static files**
```bash
python manage.py collectstatic --no-input
```

8. **Run the development server**
```bash
python manage.py runserver
```

9. **Access the application**
   - Main app: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Project Structure

```
Claims_management/
├── Audit_app/                 # Main Django project
│   ├── settings.py           # Django settings
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI application
├── claims/                   # Main application
│   ├── models.py            # Database models
│   ├── views.py             # View logic
│   ├── urls.py              # App URLs
│   ├── forms.py             # Django forms
│   ├── admin.py             # Admin configuration
│   ├── middleware.py        # Custom middleware
│   └── templatetags/        # Custom template filters
├── templates/               # HTML templates
│   ├── base.html           # Base template
│   ├── claims/             # Claims app templates
│   └── auth/               # Authentication templates
├── static/                 # Static files (CSS, JS, images)
│   ├── css/
│   ├── images/
│   └── js/
├── media/                  # User uploads
├── staticfiles/            # Collected static files (auto-generated)
├── requirements.txt        # Python dependencies
├── build.sh               # Render deployment script
└── manage.py              # Django management script
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEBUG` | Enable debug mode | `False` | No |
| `SECRET_KEY` | Django secret key | Auto-generated | Production |
| `EMAIL_HOST_USER` | SMTP email username | None | Email features |
| `EMAIL_HOST_PASSWORD` | SMTP email password | None | Email features |

### Local Development

For local development, set `DEBUG=True` in your environment:

```bash
# Windows
set DEBUG=True
python manage.py runserver

# macOS/Linux
export DEBUG=True
python manage.py runserver
```

## Deployment

### Render.com Deployment

This application is configured for automatic deployment on Render.com:

1. **Connect GitHub repository** to Render
2. **Create Web Service** with these settings:
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn Audit_app.wsgi:application`
   - **Environment Variables**:
     - `DEBUG=False`
     - `PYTHON_VERSION=3.11.9`

3. **Automatic deployments** trigger on every git push to main branch

### Manual Deployment Steps

1. **Prepare for deployment**
```bash
python manage.py collectstatic --no-input
python manage.py migrate
```

2. **Commit and push changes**
```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

3. **Render automatically builds and deploys** the application

## Database Schema

### Key Models

- **Claim** - Main claims data with status, amounts, dates
- **ClaimNote** - Notes attached to claims (admin/user/system)
- **UserProfile** - Extended user profiles with pictures

### Sample Data

The application includes sample claims data. To load additional test data:

```bash
python manage.py shell
# Run custom data loading scripts
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Claims list with pagination |
| `/claim/<claim_id>/` | GET | Claim detail modal |
| `/api/search/` | GET | HTMX search endpoint |
| `/api/flag/<claim_id>/` | POST | Toggle claim flag |
| `/api/add-note/<claim_id>/` | POST | Add note to claim |
| `/profile/` | GET/POST | User profile management |
| `/auth/login/` | GET/POST | User authentication |

## Features in Detail

### Pagination System
- 25 claims per page for optimal performance
- HTMX-powered pagination without page reloads
- Maintains search/filter state across pages

### Search & Filtering
- Real-time search with 300ms debounce
- Filter by claim status (denied, paid, under review, flagged)
- Combines with pagination seamlessly

### Mobile Responsiveness
- Horizontal scrolling tables with sticky first column
- Clickable rows for better mobile experience
- Progressive column hiding on smaller screens

### Security Features
- CSRF protection enabled
- Secure headers in production
- User authentication required
- Media file serving with custom middleware

## Development

### Adding New Features

1. **Create models** in `claims/models.py`
2. **Create migrations**: `python manage.py makemigrations`
3. **Apply migrations**: `python manage.py migrate`
4. **Add views** in `claims/views.py`
5. **Update templates** in `templates/claims/`
6. **Add CSS styles** in `static/css/claims.css`

### Code Style

- Follow Django best practices
- Use HTMX for dynamic interactions
- Bootstrap classes for styling
- Descriptive commit messages

## Troubleshooting

### Common Issues

**Local server shows SSL errors:**
```bash
# Ensure DEBUG=True for local development
set DEBUG=True  # Windows
export DEBUG=True  # macOS/Linux
```

**Static files not loading:**
```bash
python manage.py collectstatic --no-input
```

**Database errors:**
```bash
python manage.py migrate
python manage.py makemigrations
python manage.py migrate
```

**Profile pictures not displaying:**
- Check that `media/` directory exists
- Verify `MEDIA_URL` and `MEDIA_ROOT` settings
- Ensure custom middleware is installed

### Performance Issues

For large datasets (5000+ claims):
- Pagination is already implemented (25 per page)
- Consider adding database indexes on frequently queried fields
- Monitor database query performance

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Commit with clear messages: `git commit -m "Add feature description"`
5. Push and create pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create GitHub issues for bugs/features
- Check existing documentation
- Review Django and HTMX documentation for framework-specific questions

## Live Demo

**Production URL**: https://claims-management-mhb2.onrender.com

**Test Credentials**: Contact administrator for demo access

---

Built with Django, HTMX, and modern web technologies for efficient insurance claim management.
