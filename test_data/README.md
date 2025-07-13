# Project Configuration

This is a sample project for testing the enhanced smart-search system.

## Features

- **Authentication System** (`auth.py`): User registration, login, and session management
- **Task Management** (`task_manager.js`): JavaScript-based task management with full CRUD operations
- **Data Processing** (`DataProcessor.java`): Java utility class for data validation and processing

## File Structure

```
test_project/
├── auth.py           # Python authentication module
├── task_manager.js   # JavaScript task management
├── DataProcessor.java # Java data processing utilities
├── README.md         # This file
├── package.json      # Node.js package configuration
├── requirements.txt  # Python dependencies
├── *.pdf             # PDF files
├── libraries/p5.min.js # Duplicated file
├── p5.min.js        # duplicated file
└── .gitignore       # Git ignore patterns
```

## Key Components

### Authentication System (Python)
- User registration and login
- Password hashing with SHA-256
- Session management
- User activation/deactivation

### Task Management (JavaScript)
- Create, update, and delete tasks
- Task filtering and search
- Priority and status management
- Comment system
- Export functionality (JSON/CSV)

### Data Processing (Java)
- String validation and sanitization
- Date formatting and parsing
- Email validation
- Text manipulation utilities
- Percentage calculations

## Usage Examples

### Python Authentication
```python
from auth import user_manager

# Register a new user
user = user_manager.register_user("john_doe", "john@example.com", "password123")

# Authenticate user
auth_user = user_manager.authenticate_user("john_doe", "password123")

# Create session
session_id = user_manager.create_session(auth_user)
```

### JavaScript Task Management
```javascript
const taskManager = new TaskManager();

// Create a new task
const task = taskManager.createTask(
    "Implement search feature",
    "Add semantic search capability to the application",
    "john_doe",
    "high"
);

// Update task status
task.updateStatus("in-progress");

// Add a comment
task.addComment("Started working on the search algorithm", "john_doe");
```

### Java Data Processing
```java
// Validate and sanitize input
String userInput = "<script>alert('xss')</script>Hello World!";
String sanitized = DataProcessor.sanitizeInput(userInput);

// Format date
LocalDateTime now = LocalDateTime.now();
String formatted = DataProcessor.formatDate(now);

// Validate email
boolean isValid = DataProcessor.isValidEmail("test@example.com");
```

## Testing

This project is designed to test the following smart-search features:

1. **Code Parsing**: Intelligent chunking of Python, JavaScript, and Java code
2. **Function Detection**: Identifying classes, methods, and functions
3. **Import Handling**: Parsing import statements and dependencies
4. **Comment Processing**: Including docstrings and comments in search
5. **Multi-language Support**: Handling different programming languages
6. **File Type Recognition**: Proper categorization of file types

## Search Scenarios

When indexed by the smart-search system, you should be able to search for:

- **Function names**: "authenticate_user", "createTask", "sanitizeInput"
- **Class names**: "User", "TaskManager", "DataProcessor"
- **Concepts**: "authentication", "task management", "data validation"
- **Comments**: "hash password", "comma-separated string", "session management"
- **Technical terms**: "SHA-256", "LocalDateTime", "JSON export"

## Performance Considerations

This test project includes:
- **Duplicate detection**: Multiple similar utility functions to test deduplication
- **Various file sizes**: From small config files to larger implementation files
- **Mixed content**: Code, documentation, and configuration files
- **Common patterns**: Typical project structure with standard files
