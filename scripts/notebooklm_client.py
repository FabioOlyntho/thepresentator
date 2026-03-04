"""
NotebookLM Client Wrapper — Generates presentations via NotebookLM MCP.

Wraps the notebooklm-mcp-cli package to provide a simple interface
for Presentation Factory's --notebooklm mode.

Pipeline: Create notebook → Upload PDF → Generate slides → Poll → Download PPTX → Cleanup
"""

import asyncio
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Generation constants
POLL_INTERVAL_SECONDS = 20
POLL_TIMEOUT_SECONDS = 600  # 10 minutes (slide generation can take 5-8 min)
INITIAL_DELAY_SECONDS = 15  # Short delay before first poll
SLIDE_FORMAT_DETAILED = 1
SLIDE_FORMAT_PRESENTER = 2
SLIDE_LENGTH_DEFAULT = 3
SLIDE_LENGTH_SHORT = 1
CREATE_RETRIES = 2
CREATE_RETRY_DELAY = 5  # seconds between retries


def _resolve_profile(profile: str | None) -> str:
    """Resolve auth profile name: explicit > config default > 'default'."""
    if profile:
        return profile
    try:
        from notebooklm_tools.cli.utils import get_config
        return get_config().auth.default_profile
    except Exception:
        return "default"


class NotebookLMPipeline:
    """Generate presentations via NotebookLM's native slide generation engine."""

    def __init__(self, profile: str | None = None):
        """
        Initialize with cached auth credentials.

        Args:
            profile: Optional auth profile name (default: uses config default).
        """
        self._profile = profile
        self._client = None

    def _get_client(self):
        """Lazily create an authenticated NotebookLMClient."""
        if self._client is not None:
            return self._client

        try:
            from notebooklm_tools.core.auth import AuthManager
            from notebooklm_tools import NotebookLMClient
        except ImportError:
            raise RuntimeError(
                "notebooklm-mcp-cli is not installed. "
                "Install it with: pip install notebooklm-mcp-cli"
            )

        profile_name = _resolve_profile(self._profile)

        manager = AuthManager(profile_name)
        if not manager.profile_exists():
            raise RuntimeError(
                f"NotebookLM auth profile '{profile_name}' not found. "
                "Run 'nlm login' to authenticate first."
            )

        p = manager.load_profile()
        self._client = NotebookLMClient(
            cookies=p.cookies,
            csrf_token=p.csrf_token or "",
            session_id=p.session_id or "",
            build_label=p.build_label or "",
        )
        return self._client

    def generate_from_pdf(
        self,
        pdf_path: str,
        output_path: str,
        prompt: str | None = None,
        slide_count: int = 8,
        language: str = "ES",
    ) -> str | None:
        """
        Full pipeline: PDF → NotebookLM → PPTX.

        Steps:
            1. Create temporary notebook
            2. Upload PDF as source
            3. Generate slide deck artifact (with custom prompt)
            4. Poll until ready (10s initial, then 30s intervals, 5min timeout)
            5. Download PPTX to output_path
            6. Cleanup: delete temporary notebook

        Args:
            pdf_path: Path to source PDF file.
            output_path: Destination path for the generated PPTX.
            prompt: Custom focus prompt for slide generation.
            slide_count: Target slide count (influences length_code selection).
            language: Language code ("ES" for Spanish, "EN" for English).

        Returns:
            output_path on success, None on failure.
        """
        pdf_path = str(pdf_path)
        output_path = str(output_path)

        if not Path(pdf_path).exists():
            logger.error("PDF not found: %s", pdf_path)
            return None

        client = self._get_client()
        notebook_id = None

        try:
            # ─── Step 1: Create temporary notebook ─────────────
            pdf_name = Path(pdf_path).stem
            notebook_title = f"PF_{pdf_name}_{int(time.time())}"
            logger.info("Creating temporary notebook: %s", notebook_title)

            notebook = client.create_notebook(title=notebook_title)
            if notebook is None:
                logger.error("Failed to create notebook")
                return None
            notebook_id = notebook.id
            logger.info("Notebook created: %s", notebook_id)

            # ─── Step 2: Upload PDF ───────────────────────────
            logger.info("Uploading PDF: %s", Path(pdf_path).name)
            try:
                source = client.add_file(notebook_id, pdf_path, wait=True, wait_timeout=120.0)
            except Exception as e:
                logger.error("Failed to upload PDF to notebook: %s", e)
                return None
            logger.info("PDF uploaded and processed")

            # ─── Step 3: Generate slide deck ──────────────────
            lang_code = "es" if language == "ES" else "en"
            length_code = SLIDE_LENGTH_SHORT if slide_count <= 5 else SLIDE_LENGTH_DEFAULT
            # Use presenter format + no custom prompt for best quality.
            # NotebookLM's internal design prompting produces significantly
            # higher-quality slides than any custom focus_prompt we provide.
            focus = prompt or ""

            logger.info("Generating slide deck (language=%s, length=%s)...", lang_code, length_code)
            result = None
            for attempt in range(1, CREATE_RETRIES + 1):
                result = client.create_slide_deck(
                    notebook_id=notebook_id,
                    format_code=SLIDE_FORMAT_PRESENTER,
                    length_code=length_code,
                    language=lang_code,
                    focus_prompt=focus,
                )
                if result is not None:
                    break
                if attempt < CREATE_RETRIES:
                    logger.warning("Attempt %d/%d failed, retrying in %ds...",
                                   attempt, CREATE_RETRIES, CREATE_RETRY_DELAY)
                    time.sleep(CREATE_RETRY_DELAY)

            if result is None:
                logger.error(
                    "NotebookLM rejected slide deck creation after %d attempts. "
                    "This usually means Google is temporarily restricting "
                    "artifact generation for your account. Try creating a slide "
                    "deck manually at https://notebooklm.google.com to verify.",
                    CREATE_RETRIES,
                )
                return None
            logger.info("Slide generation triggered")

            # ─── Step 4: Poll until ready ─────────────────────
            # create_slide_deck already returns the artifact_id
            artifact_id = result.get("artifact_id")
            if not artifact_id:
                logger.error("No artifact_id in generation result")
                return None

            deadline = time.monotonic() + POLL_TIMEOUT_SECONDS

            # Short initial delay before first poll
            time.sleep(INITIAL_DELAY_SECONDS)

            while time.monotonic() < deadline:
                elapsed = int(POLL_TIMEOUT_SECONDS - (deadline - time.monotonic()))
                logger.info("Polling... (%ds/%ds)", elapsed, POLL_TIMEOUT_SECONDS)

                status_list = client.get_studio_status(notebook_id)
                if status_list:
                    for item in status_list:
                        if not isinstance(item, dict):
                            continue
                        if item.get("artifact_id") != artifact_id:
                            continue
                        status_val = item.get("status", "")
                        if status_val == "completed":
                            logger.info("Slide deck ready (artifact_id=%s)", artifact_id)
                            break
                        elif status_val == "failed":
                            logger.error("Slide generation failed: %s", item)
                            return None
                    else:
                        # Inner loop didn't break — not ready yet
                        time.sleep(POLL_INTERVAL_SECONDS)
                        continue
                    # Inner loop broke — artifact is ready
                    break
                else:
                    time.sleep(POLL_INTERVAL_SECONDS)
            else:
                logger.error("Slide generation timed out after %ds", POLL_TIMEOUT_SECONDS)
                return None

            # ─── Step 5: Download PPTX ────────────────────────
            logger.info("Downloading slide deck as PPTX...")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # download_slide_deck is async — run via asyncio
            downloaded = asyncio.run(client.download_slide_deck(
                notebook_id=notebook_id,
                output_path=output_path,
                artifact_id=artifact_id,
                file_format="pptx",
            ))
            if downloaded and Path(downloaded).exists():
                size = Path(downloaded).stat().st_size
                logger.info("PPTX downloaded: %s (%d bytes)", downloaded, size)
                return downloaded
            else:
                logger.error("Download failed or file not found")
                return None

        except Exception as e:
            logger.error("NotebookLM pipeline error: %s", e, exc_info=True)
            return None

        finally:
            # ─── Step 6: Cleanup ──────────────────────────────
            if notebook_id:
                try:
                    logger.info("Cleaning up temporary notebook...")
                    client.delete_notebook(notebook_id)
                    logger.info("Notebook deleted")
                except Exception as e:
                    logger.warning("Failed to delete notebook %s: %s", notebook_id, e)

    def _build_prompt(self, language: str, slide_count: int) -> str:
        """Construct fallback prompt (only used when caller passes explicit prompt=...)."""
        lang_label = "Spanish" if language == "ES" else "English"
        return (
            f"Create a professional {slide_count}-slide presentation in {lang_label}. "
            f"Use varied layouts: data visualizations, comparisons, quotes, infographics. "
            f"Focus on key insights and actionable takeaways."
        )

    @staticmethod
    def is_authenticated(profile: str | None = None) -> bool:
        """Check if NotebookLM auth credentials exist."""
        try:
            from notebooklm_tools.core.auth import AuthManager
        except ImportError:
            return False

        profile_name = _resolve_profile(profile)
        manager = AuthManager(profile_name)
        return manager.profile_exists()
