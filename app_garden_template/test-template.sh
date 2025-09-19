#!/bin/bash

# Simple script to test the enhanced template

echo "🧪 Testing App Garden Template Enhancements..."

# Test backend
echo ""
echo "📦 Testing Backend..."
cd backend

# Check if Python dependencies can be installed
echo "  ✓ Checking requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo "    Found requirements.txt with $(wc -l < requirements.txt) dependencies"
fi

# Check new files exist
echo "  ✓ Checking new backend files..."
for file in "app/models/base.py" "app/models/examples.py" "app/core/errors.py" "app/middleware/error_handler.py" "app/services/base_service.py" "app/services/file_parser.py"; do
    if [ -f "$file" ]; then
        echo "    ✅ $file"
    else
        echo "    ❌ Missing: $file"
    fi
done

# Test Python imports
echo "  ✓ Testing Python imports..."
python3 -c "
try:
    from app.models.base import BaseResponse, ErrorResponse
    from app.core.errors import AppError
    print('    ✅ Core imports working')
except Exception as e:
    print(f'    ❌ Import error: {e}')
"

cd ..

# Test frontend
echo ""
echo "🎨 Testing Frontend..."
cd frontend

# Check new component files
echo "  ✓ Checking new component files..."
for file in "components/ui/file-upload.tsx" "components/ui/loading-states.tsx" "components/ui/modal.tsx" "components/ui/toast.tsx" "components/ui/error-boundary.tsx" "components/ui/collapsible.tsx"; do
    if [ -f "$file" ]; then
        echo "    ✅ $file"
    else
        echo "    ❌ Missing: $file"
    fi
done

# Check enhanced files
echo "  ✓ Checking enhanced files..."
for file in "lib/api-client.ts" "styles/theme.css"; do
    if [ -f "$file" ]; then
        echo "    ✅ $file"
    else
        echo "    ❌ Missing: $file"
    fi
done

cd ..

# Check documentation
echo ""
echo "📚 Testing Documentation..."
for file in "TEMPLATE_GUIDE.md" "TEMPLATE_ENHANCEMENTS.md"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file ($(wc -l < "$file") lines)"
    else
        echo "  ❌ Missing: $file"
    fi
done

# Summary
echo ""
echo "🎉 Template Enhancement Test Complete!"
echo ""
echo "Key Features Added:"
echo "  • Pydantic models with response_format pattern"
echo "  • Comprehensive error handling framework"
echo "  • File parsing for multiple formats"
echo "  • Reusable UI component library"
echo "  • Enhanced API client with retry logic"
echo "  • Kamiwaza theme system"
echo "  • Complete documentation"
echo ""
echo "To start using the template:"
echo "  1. Install backend deps: cd backend && pip install -r requirements.txt"
echo "  2. Install frontend deps: cd frontend && npm install"
echo "  3. Start development: ./start-dev.sh"
echo ""
echo "For Docker deployment: ./scripts/build-appgarden.sh"