import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';

const EXCLUDED_HEADERS = new Set([
  'host', 'connection', 'content-length', 'transfer-encoding',
  'upgrade', 'http2-settings', 'te', 'trailer',
]);

async function handler(request: NextRequest, method: string) {
  try {
    // Build target URL
    const pathSegments = request.nextUrl.pathname.split('/').slice(2); // Remove /api
    const path = pathSegments.join('/');
    const queryString = request.nextUrl.search;
    const targetUrl = `${BACKEND_URL}/api/${path}${queryString}`;
    
    // Forward headers
    const headers: Record<string, string> = {};
    request.headers.forEach((value, key) => {
      if (!EXCLUDED_HEADERS.has(key.toLowerCase())) {
        headers[key] = value;
      }
    });
    
    // Prepare fetch options
    const fetchOptions: RequestInit = {
      method,
      headers,
      cache: 'no-store',
    };
    
    // Add body for methods that support it
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
      const contentType = request.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        fetchOptions.body = JSON.stringify(await request.json());
      } else {
        fetchOptions.body = request.body;
      }
      // @ts-expect-error - duplex required by Next.js
      fetchOptions.duplex = 'half';
    }
    
    // Make request to backend
    const response = await fetch(targetUrl, fetchOptions);
    
    // Handle streaming responses
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/event-stream')) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }
    
    // Handle normal responses
    if (response.status === 204) {
      return new Response(null, { status: 204 });
    }
    
    const data = await response.arrayBuffer();
    return new NextResponse(data, {
      status: response.status,
      headers: Object.fromEntries(response.headers),
    });
  } catch (error) {
    console.error(`[API Proxy] Error:`, error);
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    );
  }
}

// Export handlers for each HTTP method
export async function GET(req: NextRequest) { return handler(req, 'GET'); }
export async function POST(req: NextRequest) { return handler(req, 'POST'); }
export async function PUT(req: NextRequest) { return handler(req, 'PUT'); }
export async function DELETE(req: NextRequest) { return handler(req, 'DELETE'); }
export async function PATCH(req: NextRequest) { return handler(req, 'PATCH'); }