$ErrorActionPreference = "Continue"

Write-Host "Starting PostgreSQL via docker-compose..."
docker-compose up -d

Write-Host "Waiting 10 seconds for PostgreSQL to initialize..."
Start-Sleep -Seconds 10

Write-Host "Checking backend setup..."
cd backend
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

Write-Host "Installing backend dependencies..."
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Running database migrations..."
& ".\venv\Scripts\python.exe" -m alembic upgrade head
cd ..

Write-Host "Starting API Server in new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; uvicorn app.main:app --reload"

Write-Host "Starting Scheduler in new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; python app/scheduler/main.py"

Write-Host "Starting Worker in new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd worker; ..\backend\venv\Scripts\activate; python main.py"

Write-Host "Checking frontend setup..."
cd frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}

Write-Host "Starting Frontend in new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
cd ..

Write-Host "All services have been started in separate windows!"
