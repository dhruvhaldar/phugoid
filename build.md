# Building Phugoid

This document provides instructions on how to set up and run the Phugoid flight dynamics engine locally.

## Prerequisite

Phugoid requires **Python 3.8+**. It is recommended to use a virtual environment for dependency management.

## Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/dhruvhaldar/phugoid.git
   cd phugoid
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Unix or MacOS
   # venv\Scripts\activate   # On Windows
   ```

3. **Install Dependencies**
   Install the required Python packages using `pip`:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application Locally

To run the local FastAPI server, use the following command:
```bash
uvicorn api.index:app --reload
```
The server will start at `http://localhost:8000` and automatically reload when you make changes. The frontend will be served at the root URL.

## Running the Examples

You can test if the environment is properly set up by running the examples (if they exist) or by invoking the tests.

## Running Tests

Phugoid uses `pytest` for unit and end-to-end testing:
```bash
pytest tests/
```

## Deployment (Vercel)

Phugoid is architectured to work as a serverless analysis tool on Vercel:
1. Make sure you have the [Vercel CLI](https://vercel.com/cli) installed or connect the repository to your Vercel Dashboard.
2. The `vercel.json` configures the backend logic (such as FastAPI integrations). Auto-deployment is supported.

## Contributing

Make sure to format code properly and ensure that all unit and E2E tests pass before creating a pull request.
