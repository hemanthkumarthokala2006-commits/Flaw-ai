#!/bin/bash
# Start Flaw AI - Complete Setup

echo "================================"
echo "🚀 Starting Flaw AI Stack"
echo "================================"

# Step 1: Start Docker containers
echo ""
echo "📦 Step 1: Starting Docker containers..."
docker-compose up -d
echo "✅ Docker containers started"

# Step 2: Wait for database to be ready
echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

# Step 3: Run database migrations
echo ""
echo "🗄️  Step 2: Applying database schema..."
docker exec -i flaw_db mysql -u root -pHemanth@170 flaw_ai < database/schema.sql
echo "✅ Database schema applied"

# Step 4: Start backend
echo ""
echo "🔧 Step 3: Starting backend server..."
cd backend
pip install -r requirements.txt > /dev/null 2>&1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Step 5: Start frontend
echo ""
echo "⚛️  Step 4: Starting frontend development server..."
cd ../frontend
npm install > /dev/null 2>&1
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "================================"
echo "✨ Flaw AI is running!"
echo "================================"
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend:  http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "🗄️  Database: localhost:3307"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background processes
wait
