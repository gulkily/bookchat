# BookChat

A simple chat application for book discussions.

## Features

- Real-time messaging
- File-based or Git-based storage
- Simple and intuitive interface

## Project Structure

```
bookchat/
├── doc/
│   └── DEVELOPMENT.md
├── server/
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── file_storage.py
│   │   ├── git_storage.py
│   │   └── git_manager.py
│   ├── __init__.py
│   ├── config.py
│   ├── handler.py
│   ├── handler_methods.py
│   ├── logger.py
│   ├── main.py
│   ├── message_handler.py
│   └── utils.py
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── index.html
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_file_storage.py
│   ├── test_git_storage.py
│   ├── test_handler_methods.py
│   └── test_message_handler.py
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── README.md
└── requirements.txt
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bookchat.git
cd bookchat
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

## Usage

1. Start the server:
```bash
python -m server.main
```

2. Open your browser to `http://localhost:8080`

## Development

See [DEVELOPMENT.md](doc/DEVELOPMENT.md) for development guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
