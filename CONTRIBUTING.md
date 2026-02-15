# Contributing to VPN Master Panel

First off, thank you for considering contributing to VPN Master Panel! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Guidelines](#coding-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## 🤝 Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

## 🚀 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When you create a bug report, include:

- **Clear title** and description
- **Steps to reproduce** the behavior
- **Expected behavior**
- **Actual behavior**
- **Screenshots** if applicable
- **Environment** (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. Provide:

- **Use case**: Describe the problem you're trying to solve
- **Proposed solution**: Your suggested implementation
- **Alternatives**: Other solutions you've considered

### Pull Requests

1. Fork the repo and create your branch from `main`
2. Make your changes
3. Add tests if applicable
4. Ensure tests pass
5. Update documentation
6. Submit the pull request

## 💻 Development Setup

### Prerequisites

```bash
# System requirements
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
```

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/vpn-master-panel.git
cd vpn-master-panel

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Frontend setup
cd ../frontend
npm install

# Start development servers
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Database (Docker)
docker-compose up postgres redis
```

## 📁 Project Structure

```
vpn-master-panel/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Database setup
│   │   ├── models/              # SQLAlchemy models
│   │   ├── api/                 # API endpoints
│   │   ├── services/            # Business logic
│   │   ├── tunnels/             # Tunnel implementations
│   │   └── utils/               # Utilities
│   └── tests/                   # Backend tests
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API clients
│   │   └── utils/               # Utilities
│   └── tests/                   # Frontend tests
├── scripts/                     # Installation scripts
├── monitoring/                  # Monitoring configs
└── docs/                        # Documentation
```

## 📝 Coding Guidelines

### Python (Backend)

```python
# Use type hints
def create_user(username: str, password: str) -> User:
    """Create a new user."""
    pass

# Follow PEP 8
# Use descriptive variable names
# Add docstrings to functions/classes

# Example class
class UserService:
    """Service for user management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user instance
            
        Raises:
            ValueError: If username already exists
        """
        # Implementation
        pass
```

### JavaScript/React (Frontend)

```javascript
// Use functional components with hooks
import React, { useState, useEffect } from 'react';

export const UserList = () => {
  const [users, setUsers] = useState([]);
  
  useEffect(() => {
    loadUsers();
  }, []);
  
  const loadUsers = async () => {
    // Implementation
  };
  
  return (
    <div className="user-list">
      {/* JSX */}
    </div>
  );
};

// Use meaningful names
// Add PropTypes or TypeScript
// Keep components small and focused
```

### Code Style

**Python:**
- Follow PEP 8
- Use `black` for formatting
- Use `flake8` for linting
- Use `mypy` for type checking

```bash
# Format code
black backend/app

# Lint
flake8 backend/app

# Type check
mypy backend/app
```

**JavaScript:**
- Use ESLint + Prettier
- Follow Airbnb style guide
- Use modern ES6+ features

```bash
# Lint and format
npm run lint
npm run format
```

## 📝 Commit Messages

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting)
- **refactor**: Code refactoring
- **test**: Adding/updating tests
- **chore**: Maintenance tasks

### Examples

```bash
feat(api): add user search endpoint

Add new endpoint to search users by username or email.
Includes pagination and filtering support.

Closes #123

---

fix(tunnel): resolve PersianShield connection timeout

Increase connection timeout from 10s to 30s to handle
slow networks. Add retry logic with exponential backoff.

Fixes #456

---

docs(readme): update installation instructions

Add Docker Compose installation steps and troubleshooting
section for common issues.
```

## 🔄 Pull Request Process

### Before Submitting

1. **Update documentation** if needed
2. **Add tests** for new features
3. **Run tests** and ensure they pass
4. **Update CHANGELOG.md**
5. **Check code style**

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Tests pass locally
- [ ] No new warnings
```

### Review Process

1. Maintainer reviews code
2. Changes may be requested
3. CI/CD checks must pass
4. Approval required from 1+ maintainer
5. Squash and merge

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_users.py
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test
npm test UserList.test.js
```

## 🐛 Debugging

### Backend

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use built-in breakpoint()
breakpoint()

# View logs
docker-compose logs -f backend
```

### Frontend

```javascript
// Use browser DevTools
console.log('Debug:', data);

// React DevTools extension
// Network tab for API calls
```

## 📚 Resources

### Documentation

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Docker Docs](https://docs.docker.com/)

### Project Specific

- [API Documentation](http://localhost:8000/docs)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Security Guidelines](docs/SECURITY.md)

## 💬 Communication

### Where to Ask Questions

- **GitHub Discussions**: General questions
- **GitHub Issues**: Bug reports, feature requests
- **Discord/Telegram**: Real-time chat (if available)

### Response Times

- Issues: 1-3 days
- PRs: 2-5 days
- Security issues: 24 hours

## 🏆 Recognition

Contributors are recognized in:
- README.md
- Release notes
- Contributors page

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to VPN Master Panel! 🎉**

Together, we're building a better, more open internet.
