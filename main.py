"""
FastAPI Application for Amazon to eBay Product Listing
Monitors folder for Amazon product exports and creates eBay listings
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
import logging

from config import settings
from file_processor import file_processor
from ebay_auth import auth_manager
from ebay_client import ebay_client
from product_mapper import product_mapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Amazon to eBay Listing Manager",
    description="Automated dropshipping tool for creating eBay listings from Amazon products",
    version="1.0.0"
)


class ProcessRequest(BaseModel):
    """Request to manually trigger file processing"""
    file_name: Optional[str] = None


class StatusResponse(BaseModel):
    """Application status response"""
    status: str
    watcher_running: bool
    watch_folder: str
    processed_count: int
    failed_count: int


@app.on_event("startup")
async def startup_event():
    """Start file watcher on application startup"""
    logger.info("Starting Amazon to eBay Listing Manager...")

    # Start file watcher
    file_processor.start_watching()

    # Process any existing files
    asyncio.create_task(file_processor.process_existing_files())

    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop file watcher on application shutdown"""
    logger.info("Shutting down...")
    file_processor.stop_watching()
    logger.info("Shutdown complete")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Home page with dashboard"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Amazon to eBay Listing Manager</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h1 {{
                color: #667eea;
                margin-bottom: 10px;
            }}
            .status {{
                background: #f0f9ff;
                border-left: 4px solid #667eea;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .info-card {{
                background: #f8fafc;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }}
            .info-card h3 {{
                margin-top: 0;
                color: #334155;
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .info-card p {{
                margin: 5px 0;
                color: #64748b;
                font-size: 14px;
            }}
            .info-card .value {{
                color: #667eea;
                font-size: 18px;
                font-weight: bold;
            }}
            .api-link {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                text-decoration: none;
                margin: 5px;
                font-weight: 600;
            }}
            .api-link:hover {{
                background: #5568d3;
            }}
            code {{
                background: #f1f5f9;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }}
            .section {{
                margin: 30px 0;
            }}
            .warning {{
                background: #fef2f2;
                border-left: 4px solid #ef4444;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
                color: #991b1b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📦 Amazon to eBay Listing Manager</h1>
            <p style="color: #666;">Automated dropshipping tool for creating eBay listings from Amazon products</p>

            <div class="status">
                <strong>Status:</strong> File watcher is running ✅<br>
                <strong>Monitoring:</strong> <code>{settings.watch_folder}</code>
            </div>

            <div class="info-grid">
                <div class="info-card">
                    <h3>Watch Folder</h3>
                    <p class="value">{settings.watch_folder.name}</p>
                    <p>Drop Amazon JSON files here</p>
                </div>
                <div class="info-card">
                    <h3>Batch Size</h3>
                    <p class="value">{settings.max_items_per_batch}</p>
                    <p>Items per eBay API request</p>
                </div>
                <div class="info-card">
                    <h3>Price Markup</h3>
                    <p class="value">{settings.price_markup_percentage}%</p>
                    <p>+ ${settings.fixed_markup_amount} fixed</p>
                </div>
                <div class="info-card">
                    <h3>Environment</h3>
                    <p class="value">{settings.ebay_environment}</p>
                    <p>eBay API Mode</p>
                </div>
            </div>

            <div class="section">
                <h2>🔗 API Endpoints</h2>
                <a href="/docs" class="api-link">📖 API Documentation</a>
                <a href="/status" class="api-link">📊 Check Status</a>
                <a href="/auth/consent-url" class="api-link">🔐 Get eBay Auth URL</a>
            </div>

            <div class="section">
                <h2>🚀 Quick Start</h2>
                <ol>
                    <li>Set up your eBay Developer credentials in <code>.env</code> file</li>
                    <li>Authorize your eBay account (visit <a href="/auth/consent-url">/auth/consent-url</a>)</li>
                    <li>Set up Business Policies in eBay Seller Hub</li>
                    <li>Export products from Amazon using the browser extension</li>
                    <li>Save JSON files to the watch folder: <code>{settings.watch_folder}</code></li>
                    <li>Files will be automatically processed and listings created!</li>
                </ol>
            </div>

            <div class="warning">
                <strong>⚠️ Important Setup Required:</strong><br>
                Before creating listings, you must:<br>
                1. Complete eBay OAuth 2.0 authorization flow<br>
                2. Create Business Policies (Payment, Return, Fulfillment) in eBay Seller Hub<br>
                3. Update policy IDs in your application code<br>
                4. Get category IDs for your products
            </div>

            <div class="section">
                <h2>📁 Folder Structure</h2>
                <p><strong>Watch:</strong> <code>{settings.watch_folder}</code></p>
                <p><strong>Processed:</strong> <code>{settings.processed_folder}</code></p>
                <p><strong>Failed:</strong> <code>{settings.failed_folder}</code></p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get application status"""
    processed_files = list(settings.processed_folder.glob("*.json"))
    failed_files = list(settings.failed_folder.glob("*_FAILED_*.json"))

    return StatusResponse(
        status="running",
        watcher_running=file_processor.observer is not None and file_processor.observer.is_alive(),
        watch_folder=str(settings.watch_folder),
        processed_count=len(processed_files),
        failed_count=len(failed_files)
    )


@app.post("/process")
async def manual_process(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """Manually trigger processing of a file or all files"""
    if request.file_name:
        file_path = settings.watch_folder / request.file_name

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_name}")

        background_tasks.add_task(file_processor.process_file, file_path)

        return {
            "message": f"Processing {request.file_name}",
            "status": "started"
        }
    else:
        # Process all existing files
        background_tasks.add_task(file_processor.process_existing_files)

        return {
            "message": "Processing all files in watch folder",
            "status": "started"
        }


@app.get("/auth/consent-url")
async def get_consent_url(state: str = "amazon-ebay-app"):
    """
    Get eBay user consent URL for OAuth authorization.

    Steps:
    1. Visit this URL
    2. Sign in to eBay and authorize the app
    3. eBay will redirect to your redirect_uri with an authorization code
    4. Exchange the code for access token using /auth/callback
    """
    consent_url = auth_manager.get_consent_url(state)

    return {
        "consent_url": consent_url,
        "instructions": [
            "1. Visit the consent_url in your browser",
            "2. Sign in to your eBay account",
            "3. Authorize the application",
            "4. You'll be redirected to your redirect_uri with a 'code' parameter",
            "5. Send that code to POST /auth/callback to get your access token"
        ]
    }


@app.post("/auth/callback")
async def auth_callback(authorization_code: str):
    """
    Exchange authorization code for access token.

    After user authorizes your app, eBay redirects to your redirect_uri
    with a 'code' parameter. Send that code here to get access token.
    """
    try:
        access_token = auth_manager.get_user_token(authorization_code)

        return {
            "success": True,
            "message": "Authorization successful! You can now create eBay listings.",
            "token_expires_in": "2 hours"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/test/mapper")
async def test_mapper():
    """Test the product mapper with sample data"""
    sample_product = {
        "asin": "B08L5Z2Q49",
        "title": "Sample Product for Testing",
        "price": "$29.99",
        "images": ["https://example.com/image1.jpg"],
        "description": "This is a test description",
        "bulletPoints": ["Feature 1", "Feature 2"],
        "specifications": {}
    }

    inventory_item = product_mapper.map_to_inventory_item(sample_product)
    amazon_price = product_mapper.parse_price(sample_product["price"])
    ebay_price = product_mapper.calculate_ebay_price(amazon_price)

    return {
        "sample_product": sample_product,
        "mapped_inventory_item": inventory_item,
        "pricing": {
            "amazon_price": amazon_price,
            "ebay_price": ebay_price,
            "markup_percentage": settings.price_markup_percentage,
            "fixed_markup": settings.fixed_markup_amount
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
