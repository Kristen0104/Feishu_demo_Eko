from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/canvas/board", response_class=HTMLResponse, summary="画板生成测试页")
async def board_ui() -> HTMLResponse:
    return HTMLResponse(
        """
        <html>
          <head>
            <title>Feishu Board Generator</title>
            <meta charset="utf-8" />
          </head>
          <body>
            <h1>Feishu Board Generator</h1>
            <form>
              <label for="sharing_url">sharing_url</label>
              <input id="sharing_url" name="sharing_url" />
              <label for="message">message</label>
              <textarea id="message" name="message"></textarea>
              <label for="syntax">syntax</label>
              <input id="syntax" name="syntax" value="plantuml" />
              <label for="diagram_type">diagram_type</label>
              <input id="diagram_type" name="diagram_type" value="auto" />
              <label for="style">style</label>
              <input id="style" name="style" value="board" />
              <label for="overwrite">overwrite</label>
              <input id="overwrite" name="overwrite" type="checkbox" />
              <label for="dry_run">dry_run</label>
              <input id="dry_run" name="dry_run" type="checkbox" />
              <button type="button">Run Task</button>
            </form>
          </body>
        </html>
        """
    )
